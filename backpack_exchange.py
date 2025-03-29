import ccxt
import hmac
import hashlib
import time
from typing import Dict, Optional, List, Tuple
from urllib.parse import urlencode
import logging
import requests
import base64
import nacl.signing
import json

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # 设置日志级别为DEBUG

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 创建格式化器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# 添加处理器到日志记录器
logger.addHandler(console_handler)

class BackpackExchange(ccxt.Exchange):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.apiKey = config.get('apiKey')
        self.secret = config.get('secret')
        self.baseUrl = 'https://api.backpack.exchange'
        self.timeout = 30000  # 30秒超时
        
        # 配置请求会话
        self.session = requests.Session()
        self.session.verify = True  # 启用 SSL 验证
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def _get_timestamp(self) -> int:
        """获取当前时间戳(毫秒)"""
        return int(time.time() * 1000)

    def _sign_request(self, method: str, path: str, params: Optional[Dict] = None, data: Optional[Dict] = None, instruction: Optional[str] = None) -> Tuple[str, Dict]:
        """
        生成请求签名
        :param method: 请求方法
        :param path: 请求路径
        :param params: 查询参数
        :param data: 请求体数据
        :param instruction: 指令类型
        :return: 签名和请求头
        """
        # 生成时间戳
        timestamp = str(int(time.time() * 1000))
        window = "5000"  # 5秒时间窗口
        
        # 准备签名字符串
        signature_parts = []
        
        # 添加指令类型（如果有）
        if instruction:
            signature_parts.append(f"instruction={instruction}")
        
        # 添加请求体数据（如果有）
        if data:
            # 对数据进行排序
            sorted_data = sorted(data.items(), key=lambda x: x[0])
            # 构建数据字符串，处理布尔值
            data_string = "&".join([
                f"{k}={str(v).lower() if isinstance(v, bool) else v}" 
                for k, v in sorted_data
            ])
            signature_parts.append(data_string)
        
        # 添加查询参数（如果有）
        if params:
            # 对参数进行排序
            sorted_params = sorted(params.items(), key=lambda x: x[0])
            # 构建查询字符串，处理列表类型的参数
            query_parts = []
            for k, v in sorted_params:
                if isinstance(v, list):
                    # 对于列表类型的参数，将每个元素单独添加
                    for item in v:
                        query_parts.append(f"{k}={item}")
                else:
                    query_parts.append(f"{k}={v}")
            query_string = "&".join(query_parts)
            signature_parts.append(query_string)
        
        # 添加时间戳和窗口
        signature_parts.append(f"timestamp={timestamp}")
        signature_parts.append(f"window={window}")
        
        # 构建完整的签名字符串
        signature_data = "&".join(signature_parts)
        
        # 使用 ED25519 生成签名
        private_key = base64.b64decode(self.secret)
        message = signature_data.encode('utf-8')
        signature = nacl.signing.SigningKey(private_key).sign(message).signature
        
        # Base64 编码签名
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # 准备请求头
        headers = {
            'X-API-KEY': self.apiKey,
            'X-SIGNATURE': signature_b64,
            'X-TIMESTAMP': timestamp,
            'X-WINDOW': window,
            'Content-Type': 'application/json'
        }
        
        # 记录调试信息
        logger.debug("签名信息:")
        logger.debug(f"时间戳: {timestamp}")
        logger.debug(f"时间窗口: {window}")
        logger.debug(f"方法: {method}")
        logger.debug(f"路径: {path}")
        logger.debug(f"查询参数: {params}")
        logger.debug(f"请求体数据: {data}")
        logger.debug(f"指令类型: {instruction}")
        logger.debug(f"签名字符串: {signature_data}")
        logger.debug(f"签名: {signature_b64}")
        
        return signature_b64, headers

    def _request(self, method: str, path: str, params: Dict = None, data: Dict = None, instruction: str = None) -> Dict:
        """
        发送请求
        :param method: 请求方法
        :param path: 请求路径
        :param params: URL参数
        :param data: 请求体数据
        :param instruction: 指令类型
        :return: 响应数据
        """
        try:
            # 生成签名和请求头
            sign_data = self._sign_request(method, path, params, data, instruction)
            
            # 构建完整URL
            url = f"{self.baseUrl}{path}"
            if params:
                # 处理列表类型的参数
                query_parts = []
                for k, v in sorted(params.items()):
                    if isinstance(v, list):
                        # 对于列表类型的参数，将每个元素单独添加
                        for item in v:
                            query_parts.append(f"{k}={item}")
                    else:
                        query_parts.append(f"{k}={v}")
                query_string = '&'.join(query_parts)
                url = f"{url}?{query_string}"
            
            # 记录请求信息
            logger.debug(f"发送请求:")
            logger.debug(f"URL: {url}")
            logger.debug(f"方法: {method}")
            logger.debug(f"参数: {params}")
            logger.debug(f"数据: {data}")
            logger.debug(f"指令类型: {instruction}")
            logger.debug(f"请求头: {sign_data[1]}")
            
            # 发送请求
            response = self.session.request(
                method=method,
                url=url,
                headers=sign_data[1],
                json=data,
                verify=True
            )
            
            # 记录响应信息
            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应头: {response.headers}")
            logger.debug(f"响应内容: {response.text}")
            
            # 检查响应状态
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise Exception("API认证失败，请检查API密钥和签名")
            elif response.status_code == 403:
                raise Exception("没有权限访问该接口")
            elif response.status_code == 404:
                raise Exception("请求的资源不存在")
            elif response.status_code == 429:
                raise Exception("请求频率超限")
            else:
                raise Exception(f"请求失败: {response.text}")
                
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL连接错误: {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"请求错误: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            raise

    def fetch_ticker(self, symbol: str, is_futures: bool = False) -> Dict:
        """获取当前行情信息"""
        path = '/api/v1/ticker'
        params = {'symbol': symbol}
        response = self._request('GET', path, params)
        return self._parse_ticker(response)

    def create_order(self, symbol: str, type: str, side: str, amount: float, 
                    price: Optional[float] = None, is_futures: bool = False,
                    leverage: Optional[int] = None, margin_type: Optional[str] = None,
                    client_id: Optional[int] = None, post_only: bool = False,
                    quote_quantity: Optional[float] = None, reduce_only: bool = False,
                    self_trade_prevention: str = 'RejectTaker', time_in_force: str = 'GTC',
                    stop_loss_limit_price: Optional[float] = None,
                    stop_loss_trigger_by: Optional[str] = None,
                    stop_loss_trigger_price: Optional[float] = None,
                    take_profit_limit_price: Optional[float] = None,
                    take_profit_trigger_by: Optional[str] = None,
                    take_profit_trigger_price: Optional[float] = None,
                    trigger_by: Optional[str] = None,
                    trigger_price: Optional[float] = None,
                    trigger_quantity: Optional[str] = None,
                    auto_lend: bool = False,
                    auto_lend_redeem: bool = False,
                    auto_borrow: bool = False,
                    auto_borrow_repay: bool = False) -> Dict:
        """
        创建新订单
        :param symbol: 交易对
        :param type: 订单类型 (Market/Limit)
        :param side: 订单方向 (Bid/Ask)
        :param amount: 订单数量
        :param price: 订单价格（限价单必填）
        :param is_futures: 是否为合约订单
        :param leverage: 杠杆倍数（合约订单）
        :param margin_type: 保证金类型（合约订单）
        :param client_id: 自定义订单ID
        :param post_only: 是否只挂单不吃单
        :param quote_quantity: 市价单的报价资产数量
        :param reduce_only: 是否只减仓（合约订单）
        :param self_trade_prevention: 自成交预防策略
        :param time_in_force: 订单有效期
        :param stop_loss_limit_price: 止损限价
        :param stop_loss_trigger_by: 止损触发参考价
        :param stop_loss_trigger_price: 止损触发价格
        :param take_profit_limit_price: 止盈限价
        :param take_profit_trigger_by: 止盈触发参考价
        :param take_profit_trigger_price: 止盈触发价格
        :param trigger_by: 触发参考价
        :param trigger_price: 触发价格
        :param trigger_quantity: 触发数量类型
        :param auto_lend: 是否允许出借（现货杠杆）
        :param auto_lend_redeem: 是否允许赎回出借（现货杠杆）
        :param auto_borrow: 是否允许借入（现货杠杆）
        :param auto_borrow_repay: 是否允许偿还借入（现货杠杆）
        :return: 订单信息
        """
        # 根据交易类型选择不同的API路径
        if is_futures:
            path = '/api/v1/futures/order'
        else:
            path = '/api/v1/order'
            
        # 格式化数量，避免科学计数法
        amount_str = f"{amount:.6f}".rstrip('0').rstrip('.')
            
        # 生成唯一的 clientId (确保在 uint32 范围内)
        if client_id is None:
            # 使用当前时间戳的后 8 位数字作为 clientId
            client_id = int(time.time() * 1000) % 100000000
            
        # 准备请求体数据
        order_data = {
            'symbol': symbol,
            'side': 'Ask' if side.upper() == 'SELL' else 'Bid',
            'orderType': type.capitalize(),  # Market 或 Limit
            'quantity': amount_str,  # 使用格式化后的数量
            'timeInForce': time_in_force,
            'postOnly': post_only,
            'reduceOnly': reduce_only,
            'selfTradePrevention': self_trade_prevention,
            'clientId': client_id
        }
        
        # 添加可选参数
        if price:
            order_data['price'] = str(price)
        if quote_quantity:
            order_data['quoteQuantity'] = str(quote_quantity)
        if stop_loss_limit_price:
            order_data['stopLossLimitPrice'] = str(stop_loss_limit_price)
        if stop_loss_trigger_by:
            order_data['stopLossTriggerBy'] = stop_loss_trigger_by
        if stop_loss_trigger_price:
            order_data['stopLossTriggerPrice'] = str(stop_loss_trigger_price)
        if take_profit_limit_price:
            order_data['takeProfitLimitPrice'] = str(take_profit_limit_price)
        if take_profit_trigger_by:
            order_data['takeProfitTriggerBy'] = take_profit_trigger_by
        if take_profit_trigger_price:
            order_data['takeProfitTriggerPrice'] = str(take_profit_trigger_price)
        if trigger_by:
            order_data['triggerBy'] = trigger_by
        if trigger_price:
            order_data['triggerPrice'] = str(trigger_price)
        if trigger_quantity:
            order_data['triggerQuantity'] = trigger_quantity
            
        # 合约订单特有参数
        if is_futures:
            if leverage:
                order_data['leverage'] = str(leverage)
            if margin_type:
                order_data['marginType'] = margin_type.lower()
                
        # 现货杠杆特有参数
        if not is_futures:
            if auto_lend:
                order_data['autoLend'] = auto_lend
            if auto_lend_redeem:
                order_data['autoLendRedeem'] = auto_lend_redeem
            if auto_borrow:
                order_data['autoBorrow'] = auto_borrow
            if auto_borrow_repay:
                order_data['autoBorrowRepay'] = auto_borrow_repay
        
        # 记录订单数据
        logger.debug(f"创建订单数据: {order_data}")
        
        response = self._request('POST', path, data=order_data, instruction='orderExecute')
        return self._parse_order(response)

    def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """
        取消订单
        :param order_id: 订单ID
        :param symbol: 交易对
        :return: 订单信息
        """
        try:
            # 准备请求体数据
            data = {
                'orderId': order_id,
                'symbol': symbol
            }
            
            # 发送取消订单请求
            response = self._request('DELETE', '/api/v1/order', data=data, instruction='orderCancel')
            
            # 检查响应状态
            if response.get('status') == 'Cancelled':
                logger.info(f"订单 {order_id} 已成功取消")
                return response
            else:
                logger.error(f"取消订单失败: {response}")
                raise Exception(f"取消订单失败: {response}")
                
        except Exception as e:
            logger.error(f"取消订单时出错: {str(e)}")
            raise

    def fetch_order(self, order_id: str, symbol: str, is_futures: bool = False) -> Dict:
        """
        获取订单信息
        :param order_id: 订单ID
        :param symbol: 交易对
        :param is_futures: 是否为合约订单（已废弃，保留参数是为了兼容性）
        :return: 订单信息
        """
        path = '/api/v1/order'
            
        # 准备查询参数
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        
        # 发送请求
        logger.info(f"获取订单信息 - {params}")
        response = self._request('GET', path, params, instruction='orderQuery')
        
        if response:
            return self._parse_order(response)
        return None

    def fetch_order_by_client_id(self, client_id: int, symbol: str, is_futures: bool = False) -> Dict:
        """
        通过客户端ID获取订单信息
        :param client_id: 客户端ID
        :param symbol: 交易对
        :param is_futures: 是否为合约订单（已废弃，保留参数是为了兼容性）
        :return: 订单信息
        """
        path = '/api/v1/order'
            
        # 准备查询参数
        params = {
            'symbol': symbol,
            'clientId': client_id
        }
        
        # 发送请求
        response = self._request('GET', path, params, instruction='orderQuery')
        
        if response:
            return self._parse_order(response)
        return None

    def fetch_markets(self) -> List[Dict]:
        """获取所有可用的交易对"""
        # 获取现货交易对
        spot_path = '/api/v1/markets'
        spot_response = self._request('GET', spot_path)
        
        # 获取合约交易对
        futures_path = '/api/v1/futures/markets'
        futures_response = self._request('GET', futures_path)
        
        # 合并并解析所有交易对
        all_markets = []
        all_markets.extend(self._parse_markets(spot_response))
        all_markets.extend(self._parse_markets(futures_response))
        return all_markets

    def fetch_balance(self) -> Dict:
        """
        获取账户余额
        :return: 账户余额信息
        """
        try:
            # 获取账户资金信息
            logger.debug(f"获取账户资金信息")
            response = self._request('GET', '/api/v1/capital', instruction='balanceQuery')
            logger.debug(f"资金信息响应: {response}")
            
            # 处理余额信息
            balances = {}
            for currency, balance_info in response.items():
                balances[currency] = {
                    'free': float(balance_info.get('available', 0)),
                    'used': float(balance_info.get('locked', 0)),
                    'total': float(balance_info.get('available', 0)) + float(balance_info.get('locked', 0))
                }
            
            logger.info(f"账户余额: {balances}")
            return balances
            
        except Exception as e:
            logger.error(f"获取账户余额时出错: {str(e)}")
            raise

    def _parse_ticker(self, response: Dict) -> Dict:
        """解析行情响应"""
        # 打印原始响应数据以便调试
        logger.info(f"原始行情数据: {response}")
        
        # 根据实际 API 响应格式解析数据
        return {
            'symbol': response['symbol'],
            'last': float(response.get('lastPrice', 0)),
            'bid': float(response.get('bidPrice', 0)),
            'ask': float(response.get('askPrice', 0)),
            'volume': float(response.get('volume', 0)),
            'high': float(response.get('high', 0)),
            'low': float(response.get('low', 0)),
            'change': float(response.get('priceChange', 0))
        }

    def _parse_order(self, order: Dict) -> Dict:
        """
        解析订单信息
        :param order: 原始订单数据
        :return: 解析后的订单信息
        """
        try:
            return {
                'id': order.get('id'),  # 使用 'id' 而不是 'orderId'
                'clientId': order.get('clientId'),
                'symbol': order.get('symbol'),
                'side': order.get('side'),
                'type': order.get('orderType'),
                'price': float(order.get('price', 0)),
                'amount': float(order.get('quantity', 0)),
                'filled': float(order.get('executedQuantity', 0)),
                'cost': float(order.get('executedQuoteQuantity', 0)),
                'status': order.get('status'),
                'timeInForce': order.get('timeInForce'),
                'postOnly': order.get('postOnly', False),
                'reduceOnly': order.get('reduceOnly', False),
                'createdAt': order.get('createdAt'),
                'triggeredAt': order.get('triggeredAt'),
                'stopLossLimitPrice': order.get('stopLossLimitPrice'),
                'stopLossTriggerBy': order.get('stopLossTriggerBy'),
                'stopLossTriggerPrice': order.get('stopLossTriggerPrice'),
                'takeProfitLimitPrice': order.get('takeProfitLimitPrice'),
                'takeProfitTriggerBy': order.get('takeProfitTriggerBy'),
                'takeProfitTriggerPrice': order.get('takeProfitTriggerPrice'),
                'triggerBy': order.get('triggerBy'),
                'triggerPrice': order.get('triggerPrice'),
                'triggerQuantity': order.get('triggerQuantity'),
                'relatedOrderId': order.get('relatedOrderId')
            }
        except Exception as e:
            logger.error(f"解析订单信息时出错: {str(e)}")
            raise

    def _parse_markets(self, response: List[Dict]) -> List[Dict]:
        """解析交易对信息"""
        markets = []
        for market in response:
            try:
                symbol = market['symbol']
                # 打印原始数据以便调试
                logger.info(f"原始市场数据: {market}")
                
                # 尝试不同的分隔符
                if '-' in symbol:
                    base, quote = symbol.split('-')
                elif '_' in symbol:
                    base, quote = symbol.split('_')
                else:
                    # 如果没有分隔符，尝试从最后3个字符分割（假设是USDC）
                    base = symbol[:-4]
                    quote = symbol[-4:]
                
                markets.append({
                    'symbol': symbol,
                    'base': base,
                    'quote': quote,
                    'active': True,
                    'type': 'spot',
                    'spot': True,
                    'futures': False
                })
                logger.info(f"解析后的交易对: {base}/{quote}")
            except Exception as e:
                logger.error(f"解析交易对 {symbol} 时出错: {str(e)}")
                continue
        return markets

    def fetch_my_trades(self, symbol: str, since: Optional[int] = None, limit: Optional[int] = None, params: Dict = {}) -> List[Dict]:
        path = '/wapi/v1/history/fills'
        
        # 构建查询参数
        query_params = {
            'symbol': symbol,
            **params
        }
        
        # 添加时间范围参数
        if since is not None:
            query_params['from'] = since
        if 'to' in params:
            query_params['to'] = params['to']
            
        # 添加分页参数
        if limit is not None:
            query_params['limit'] = min(limit, 1000)  # 限制最大值为1000
        if 'offset' in params:
            query_params['offset'] = params['offset']
            
        # 添加成交类型参数
        if 'fillType' in params:
            query_params['fillType'] = params['fillType']
            
        # 添加市场类型参数
        if 'marketType' in params:
            query_params['marketType'] = params['marketType']
            
        # 发送请求
        response = self._request('GET', path, query_params, instruction='fillHistoryQueryAll')
        
        # 解析成交记录
        trades = []
        for trade in response:
            # 将 ISO 8601 格式的时间戳转换为毫秒时间戳
            timestamp_str = trade.get('timestamp')
            if timestamp_str:
                # 移除毫秒部分，只保留到秒
                timestamp_str = timestamp_str.split('.')[0]
                # 将 ISO 8601 格式转换为时间戳
                timestamp = int(time.mktime(time.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')) * 1000)
            else:
                timestamp = None
                
            parsed_trade = {
                'id': str(trade.get('tradeId')),  # 使用 tradeId 作为成交ID
                'order': trade.get('orderId'),
                'clientId': trade.get('clientId'),
                'timestamp': timestamp,
                'datetime': trade.get('timestamp'),  # 直接使用原始的时间戳字符串
                'symbol': trade.get('symbol'),
                'side': 'buy' if trade.get('side') == 'Bid' else 'sell',
                'price': float(trade.get('price')),
                'amount': float(trade.get('quantity')),
                'cost': float(trade.get('price')) * float(trade.get('quantity')),
                'fee': {
                    'currency': trade.get('feeSymbol'),
                    'cost': float(trade.get('fee')),
                    'rate': float(trade.get('fee')) / (float(trade.get('price')) * float(trade.get('quantity')))
                },
                'isMaker': trade.get('isMaker', False),
                'systemOrderType': trade.get('systemOrderType')
            }
            trades.append(parsed_trade)
            
        return trades 