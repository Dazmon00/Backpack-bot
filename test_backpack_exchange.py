import os
from dotenv import load_dotenv
from backpack_exchange import BackpackExchange
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_api_keys():
    """检查 API 密钥是否正确加载"""
    # 打印所有环境变量
    logger.debug("当前环境变量:")
    for key, value in os.environ.items():
        if 'BACKPACK' in key:
            logger.debug(f"{key}: {value}")
    
    # 检查 .env 文件是否存在
    if not os.path.exists('.env'):
        logger.error(".env 文件不存在")
        raise ValueError(".env 文件不存在")
    
    # 检查环境变量
    api_key = os.getenv('BACKPACK_API_KEY')
    api_secret = os.getenv('BACKPACK_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("API 密钥未正确加载")
        logger.error(f"BACKPACK_API_KEY: {'已设置' if api_key else '未设置'}")
        logger.error(f"BACKPACK_API_SECRET: {'已设置' if api_secret else '未设置'}")
        raise ValueError("请在 .env 文件中设置 BACKPACK_API_KEY 和 BACKPACK_API_SECRET")
    
    logger.info("API 密钥加载成功")
    return api_key, api_secret

def test_fetch_ticker():
    """测试获取行情信息"""
    try:
        # 检查 API 密钥
        api_key, api_secret = check_api_keys()
        
        exchange = BackpackExchange({
            'apiKey': api_key,
            'secret': api_secret
        })
        
        # 测试现货行情
        spot_ticker = exchange.fetch_ticker('BTC_USDC', is_futures=False)
        logger.info(f"现货行情: {spot_ticker}")
        
        # 测试合约行情
        futures_ticker = exchange.fetch_ticker('BTC_USDC', is_futures=True)
        logger.info(f"合约行情: {futures_ticker}")
        
    except Exception as e:
        logger.error(f"测试获取行情失败: {str(e)}")

def test_fetch_balance():
    """测试获取账户余额"""
    try:
        # 检查 API 密钥
        api_key, api_secret = check_api_keys()
        
        exchange = BackpackExchange({
            'apiKey': api_key,
            'secret': api_secret
        })
        
        balance = exchange.fetch_balance()
        logger.info(f"账户余额: {balance}")
        
    except Exception as e:
        logger.error(f"测试获取余额失败: {str(e)}")

def test_fetch_markets():
    """测试获取交易对信息"""
    try:
        # 检查 API 密钥
        api_key, api_secret = check_api_keys()
        
        exchange = BackpackExchange({
            'apiKey': api_key,
            'secret': api_secret
        })
        
        markets = exchange.fetch_markets()
        logger.info(f"交易对列表: {markets}")
        
    except Exception as e:
        logger.error(f"测试获取交易对失败: {str(e)}")

def test_create_order():
    """测试创建订单"""
    try:
        # 检查 API 密钥
        api_key, api_secret = check_api_keys()
        
        exchange = BackpackExchange({
            'apiKey': api_key,
            'secret': api_secret
        })
        
        # 先获取账户余额
        balance = exchange.fetch_balance()
        logger.info(f"账户余额: {balance}")
        
        # 检查 USDC 余额
        usdc_balance = balance.get('USDC', {}).get('free', 0)
        logger.info(f"USDC 可用余额: {usdc_balance}")
        
        # 先获取当前市场价格
        symbol = 'ETH_USDC'
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        logger.info(f"当前市场价格: {current_price}")
        
        # 计算可买入的 ETH 数量（使用 95% 的可用余额）
        available_usdc = usdc_balance * 0.1
        amount = round(available_usdc / current_price, 4)  # ETH 数量保留 4 位小数
        price = round(current_price * 0.95, 1)  # 价格保留 1 位小数
        
        # 格式化数量，避免科学计数法
        amount_str = f"{amount:.4f}".rstrip('0').rstrip('.')
        
        logger.info(f"计划下单数量: {amount_str} ETH")
        logger.info(f"计划下单价格: {price} USDC")
        logger.info(f"预计使用金额: {amount * price} USDC")
        
        # 测试创建现货限价买单
        spot_order = exchange.create_order(
            symbol=symbol,
            type='limit',
            side='buy',
            amount=float(amount_str),  # 使用格式化后的数量
            price=price,
            is_futures=False
        )
        logger.info(f"创建现货订单: {spot_order}")
        
        # 测试创建合约限价买单
        futures_order = exchange.create_order(
            symbol=symbol,
            type='limit',
            side='buy',
            amount=float(amount_str),  # 使用格式化后的数量
            price=price,
            is_futures=True,
            leverage=2,
            margin_type='isolated'
        )
        logger.info(f"创建合约订单: {futures_order}")
        
    except Exception as e:
        logger.error(f"测试创建订单失败: {str(e)}")

def test_cancel_order():
    """测试取消订单"""
    try:
        # 检查 API 密钥
        api_key, api_secret = check_api_keys()
        
        exchange = BackpackExchange({
            'apiKey': api_key,
            'secret': api_secret
        })
        
        # 测试取消现货订单
        spot_cancel = exchange.cancel_order(
            order_id='your_order_id',
            symbol='BTC_USDC',
            is_futures=False
        )
        logger.info(f"取消现货订单: {spot_cancel}")
        
        # 测试取消合约订单
        futures_cancel = exchange.cancel_order(
            order_id='your_order_id',
            symbol='BTC_USDC',
            is_futures=True
        )
        logger.info(f"取消合约订单: {futures_cancel}")
        
    except Exception as e:
        logger.error(f"测试取消订单失败: {str(e)}")

def test_fetch_order():
    """测试获取订单信息"""
    try:
        # 检查 API 密钥
        api_key, api_secret = check_api_keys()
        
        exchange = BackpackExchange({
            'apiKey': api_key,
            'secret': api_secret
        })
        
        # 测试获取现货订单
        spot_order = exchange.fetch_order(
            order_id='your_order_id',
            symbol='BTC_USDC',
            is_futures=False
        )
        logger.info(f"现货订单信息: {spot_order}")
        
        # 测试获取合约订单
        futures_order = exchange.fetch_order(
            order_id='your_order_id',
            symbol='BTC_USDC',
            is_futures=True
        )
        logger.info(f"合约订单信息: {futures_order}")
        
    except Exception as e:
        logger.error(f"测试获取订单信息失败: {str(e)}")

def test_fetch_my_trades():
    """测试获取成交历史"""
    try:
        # 检查 API 密钥
        api_key, api_secret = check_api_keys()
        
        # 创建交易所实例
        exchange = BackpackExchange({
            'apiKey': api_key,
            'secret': api_secret
        })
        
        # 获取成交历史
        trades = exchange.fetch_my_trades('ETH_USDC')
        
        # 打印成交历史
        logger.info("\n成交历史:")
        for trade in trades:
            logger.info(f"成交ID: {trade['id']}")
            logger.info(f"订单ID: {trade['order']}")
            logger.info(f"客户端ID: {trade['clientId']}")
            logger.info(f"时间: {trade['datetime']}")
            logger.info(f"交易对: {trade['symbol']}")
            logger.info(f"方向: {trade['side']}")
            logger.info(f"价格: {trade['price']}")
            logger.info(f"数量: {trade['amount']}")
            logger.info(f"金额: {trade['cost']}")
            logger.info(f"手续费: {trade['fee']['cost']} {trade['fee']['currency']} ({trade['fee']['rate']*100:.4f}%)")
            logger.info(f"是否挂单: {trade['isMaker']}")
            logger.info(f"系统订单类型: {trade['systemOrderType']}")
            logger.info("-" * 50)
            
        # 验证返回的数据格式
        assert isinstance(trades, list), "返回的数据应该是列表"
        if trades:  # 如果有成交记录
            trade = trades[0]
            assert 'id' in trade, "成交记录应该包含成交ID"
            assert 'order' in trade, "成交记录应该包含订单ID"
            assert 'clientId' in trade, "成交记录应该包含客户端ID"
            assert 'timestamp' in trade, "成交记录应该包含时间戳"
            assert 'datetime' in trade, "成交记录应该包含日期时间"
            assert 'symbol' in trade, "成交记录应该包含交易对"
            assert 'side' in trade, "成交记录应该包含交易方向"
            assert 'price' in trade, "成交记录应该包含价格"
            assert 'amount' in trade, "成交记录应该包含数量"
            assert 'cost' in trade, "成交记录应该包含金额"
            assert 'fee' in trade, "成交记录应该包含手续费信息"
            assert 'isMaker' in trade, "成交记录应该包含是否挂单信息"
            assert 'systemOrderType' in trade, "成交记录应该包含系统订单类型"
            
            # 验证数值类型
            assert isinstance(trade['price'], float), "价格应该是浮点数"
            assert isinstance(trade['amount'], float), "数量应该是浮点数"
            assert isinstance(trade['cost'], float), "金额应该是浮点数"
            assert isinstance(trade['fee']['cost'], float), "手续费应该是浮点数"
            assert isinstance(trade['fee']['rate'], float), "手续费率应该是浮点数"
            
            # 验证数值合理性
            assert trade['price'] > 0, "价格应该大于0"
            assert trade['amount'] > 0, "数量应该大于0"
            assert trade['cost'] > 0, "金额应该大于0"
            assert trade['fee']['cost'] >= 0, "手续费应该大于等于0"
            assert 0 <= trade['fee']['rate'] <= 1, "手续费率应该在0到1之间"
            
        logger.info("获取成交历史测试通过")
        
    except Exception as e:
        logger.error(f"获取成交历史测试失败: {str(e)}")
        raise

if __name__ == "__main__":
    # 加载环境变量
    load_dotenv(override=True)  # 添加 override=True 确保覆盖已存在的环境变量
    
    
    # # 测试获取账户余额
    # logger.info(f"================测试获取账户余额")
    # test_fetch_balance()

    # # 测试获取行情信息
    # logger.info(f"================测试获取行情信息")
    # test_fetch_ticker() 

    # # 测试获取订单信息
    # # logger.info(f"测试获取订单信息")
    # # test_fetch_order()

    # # # 测试创建订单
    # logger.info(f"================测试创建订单")
    # test_create_order() 

    # # 测试取消订单
    # test_cancel_order()

    # # 测试获取订单信息
    # test_fetch_order()

    # # 测试获取交易对信息
    # test_fetch_markets()

    # # 测试获取成交历史
    logger.info(f"================测试获取成交历史")
    test_fetch_my_trades()


