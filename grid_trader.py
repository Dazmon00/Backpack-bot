import os
import time
import logging
import signal
import sys
from typing import List, Dict
from decimal import Decimal
from dotenv import load_dotenv
from backpack_exchange import BackpackExchange
from dataclasses import dataclass
from datetime import datetime

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class OrderInfo:
    """订单信息类"""
    order_id: str
    symbol: str
    side: str  # 'bid' 或 'ask'
    price: float
    amount: float
    status: str  # 'open', 'closed', 'cancelled'
    created_at: datetime
    closed_at: datetime = None
    filled_price: float = None
    filled_amount: float = None
    profit: float = None

class OrderManager:
    """订单管理器"""
    def __init__(self):
        self.orders: Dict[str, OrderInfo] = {}  # order_id -> OrderInfo
        
    def add_order(self, order: OrderInfo):
        """添加新订单"""
        self.orders[order.order_id] = order
        logger.info(f"添加新订单: {order.order_id} - {order.side} {order.amount} @ {order.price}")
        
    def update_order(self, order_id: str, status: str, filled_price: float = None, filled_amount: float = None):
        """更新订单状态"""
        if order_id in self.orders:
            order = self.orders[order_id]
            order.status = status
            if status in ['closed', 'cancelled']:
                order.closed_at = datetime.now()
            if filled_price and filled_amount:
                order.filled_price = filled_price
                order.filled_amount = filled_amount
                if order.side == 'ask':  # 如果是卖单，计算利润
                    order.profit = (filled_price - order.price) * filled_amount
            logger.info(f"更新订单状态: {order_id} -> {status}")
            
    def get_order(self, order_id: str) -> OrderInfo:
        """获取订单信息"""
        return self.orders.get(order_id)
        
    def get_open_orders(self) -> List[OrderInfo]:
        """获取所有未完成订单"""
        return [order for order in self.orders.values() if order.status == 'open']
        
    def get_closed_orders(self) -> List[OrderInfo]:
        """获取所有已完成订单"""
        return [order for order in self.orders.values() if order.status == 'closed']
        
    def get_total_profit(self) -> float:
        """获取总利润"""
        return sum(order.profit for order in self.orders.values() if order.profit is not None)
        
    def print_order_summary(self):
        """打印订单汇总信息"""
        open_orders = self.get_open_orders()
        closed_orders = self.get_closed_orders()
        total_profit = self.get_total_profit()
        
        logger.info("\n=== 订单汇总信息 ===")
        logger.info(f"未完成订单数量: {len(open_orders)}")
        logger.info(f"已完成订单数量: {len(closed_orders)}")
        logger.info(f"总利润: {total_profit:.2f}")
        
        if closed_orders:
            logger.info("\n最近完成的订单:")
            for order in closed_orders[-5:]:  # 显示最近5个完成的订单
                logger.info(f"订单 {order.order_id}: {order.side} {order.amount} @ {order.price} -> {order.filled_price} | 利润: {order.profit:.2f}")
        logger.info("=" * 50)

class GridTrader:
    def __init__(self):
        # 初始化交易所
        self.exchange = BackpackExchange({
            'apiKey': os.getenv('API_KEY'),
            'secret': os.getenv('API_SECRET')
        })
        
        # 初始化订单管理器
        self.order_manager = OrderManager()
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 加载配置
        self.symbol = os.getenv('SYMBOL')
        self.upper_price = float(os.getenv('UPPER_PRICE'))
        self.lower_price = float(os.getenv('LOWER_PRICE'))
        self.grid_number = int(os.getenv('GRID_NUMBER'))
        self.investment = float(os.getenv('INVESTMENT'))
        self.grid_type = os.getenv('GRID_TYPE')
        self.min_order_size = float(os.getenv('MIN_ORDER_SIZE'))
        self.post_only = os.getenv('POST_ONLY').lower() == 'true'
        self.time_in_force = os.getenv('TIME_IN_FORCE')
        self.max_orders = int(os.getenv('MAX_ORDERS'))
        self.stop_loss_price = float(os.getenv('STOP_LOSS_PRICE'))
        self.take_profit_price = float(os.getenv('TAKE_PROFIT_PRICE'))
        self.check_interval = int(os.getenv('CHECK_INTERVAL'))
        
        # 初始化网格价格列表
        self.grid_prices = self.calculate_grid_prices()
        logger.info(f"网格价格列表: {self.grid_prices}")
        
        # 打印网格信息
        self.print_grid_info()
        
    def signal_handler(self, signum, frame):
        """处理退出信号"""
        logger.info("\n收到退出信号，正在关闭...")
        try:
            # 取消所有未完成订单
            self.cancel_all_orders()
            # 打印最终状态
            self.order_manager.print_order_summary()
            logger.info("程序已安全退出")
        except Exception as e:
            logger.error(f"退出时发生错误: {e}")
        finally:
            sys.exit(0)

    def print_grid_info(self):
        """打印网格信息"""
        logger.info("\n=== 网格交易配置信息 ===")
        logger.info(f"交易对: {self.symbol}")
        logger.info(f"网格类型: {'等差' if self.grid_type == 'arithmetic' else '等比'}")
        logger.info(f"总投资金额: {self.investment}")
        logger.info(f"网格数量: {self.grid_number}")
        logger.info(f"价格区间: {self.lower_price} - {self.upper_price}")
        logger.info(f"止损价格: {self.stop_loss_price}")
        logger.info(f"止盈价格: {self.take_profit_price}")
        
        # 获取并显示账户余额
        try:
            balance = self.exchange.fetch_balance()
            # 从交易对中获取基础货币和计价货币
            try:
                base_currency, quote_currency = self.symbol.split('_')
            except ValueError:
                logger.error(f"交易对格式错误: {self.symbol}，应为 BASE_QUOTE 格式")
                return
            
            base_balance = float(balance.get(base_currency, {}).get('free', 0))
            quote_balance = float(balance.get(quote_currency, {}).get('free', 0))
            logger.info(f"当前{base_currency}余额: {base_balance:.3f}")
            logger.info(f"当前{quote_currency}余额: {quote_balance:.2f}")
        except Exception as e:
            logger.error(f"获取余额错误: {e}")
        
        logger.info("\n=== 网格列表 ===")
        
        # 计算每个网格的投资金额
        grid_investment = self.investment / self.grid_number
        
        for i in range(len(self.grid_prices) - 1):
            buy_price = self.grid_prices[i]
            sell_price = self.grid_prices[i + 1]
            amount = self.get_order_amount(buy_price)
            investment = amount * buy_price
            profit = amount * (sell_price - buy_price)
            profit_percentage = (profit / investment) * 100
            
            logger.info(f"网格 {i+1}: {buy_price:.2f} -> {sell_price:.2f} | "
                       f"投入: {investment:.2f} | "
                       f"收益: {profit:.2f} ({profit_percentage:.2f}%)")
        
        logger.info("\n=== 风险提示 ===")
        logger.info(f"最小订单数量: {self.min_order_size}")
        logger.info(f"最大订单数量: {self.max_orders}")
        logger.info(f"检查间隔: {self.check_interval}秒")
        logger.info("=" * 50 + "\n")

    def calculate_grid_prices(self) -> List[float]:
        """计算网格价格"""
        prices = []
        if self.grid_type == 'arithmetic':
            # 等差网格
            step = (self.upper_price - self.lower_price) / self.grid_number
            for i in range(self.grid_number + 1):
                price = self.lower_price + step * i
                prices.append(round(price, 2))
        else:
            # 等比网格
            ratio = (self.upper_price / self.lower_price) ** (1.0 / self.grid_number)
            for i in range(self.grid_number + 1):
                price = self.lower_price * (ratio ** i)
                prices.append(round(price, 2))
        return prices

    def get_order_amount(self, price: float) -> float:
        """计算订单数量"""
        grid_investment = self.investment / self.grid_number
        amount = grid_investment / price
        return max(round(amount, 2), self.min_order_size)

    def check_balance(self, side: str, amount: float, price: float) -> bool:
        """检查账户余额是否足够"""
        try:
            balance = self.exchange.fetch_balance()
            # 从交易对中获取基础货币和计价货币
            try:
                base_currency, quote_currency = self.symbol.split('_')
            except ValueError:
                logger.error(f"交易对格式错误: {self.symbol}，应为 BASE_QUOTE 格式")
                return False
            
            if side == 'bid':
                # 检查计价货币余额是否足够
                required_quote = amount * price
                quote_balance = float(balance.get(quote_currency, {}).get('free', 0))
                if quote_balance < required_quote:
                    logger.warning(f"{quote_currency}余额不足: 需要 {required_quote:.2f} {quote_currency}, 当前余额 {quote_balance:.2f} {quote_currency}")
                    return False
            else:
                # 检查基础货币余额是否足够
                base_balance = float(balance.get(base_currency, {}).get('free', 0))
                if base_balance < amount:
                    logger.warning(f"{base_currency}余额不足: 需要 {amount:.3f} {base_currency}, 当前余额 {base_balance:.3f} {base_currency}")
                    return False
            return True
        except Exception as e:
            logger.error(f"检查余额错误: {e}")
            return False

    def place_grid_orders(self):
        """布置网格订单"""
        try:
            # 获取当前价格
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = float(ticker['last'])
            logger.info(f"当前价格: {current_price}")

            # 取消所有未完成的订单
            self.cancel_all_orders()

            # 计算价格范围限制（比如当前价格的±10%）
            price_range = 0.1  # 10%的价格范围
            min_price = current_price * (1 - price_range)
            max_price = current_price * (1 + price_range)


            # 在当前价格上下布置订单
            for price in self.grid_prices:
                # 只在下单价格在允许范围内时下单
                if min_price <= price <= max_price:
                    amount = self.get_order_amount(price)
                    if price < current_price:
                        logger.info(f"当前价格: {current_price}，下方布置买单{float(amount)} {float(price)}")
                        if self.check_balance('bid', amount, price):
                            self.place_order('bid', amount, price)
                    elif price > current_price:
                        logger.info(f"当前价格: {current_price}，上方布置卖单{float(amount)} {float(price)}")
                        if self.check_balance('ask', amount, price):
                            self.place_order('ask', amount, price)
                else:
                    logger.info(f"跳过价格 {float(price)}，超出允许范围 ({float(min_price):.2f} - {float(max_price):.2f})")
                
        except Exception as e:
            logger.error(f"布置网格订单错误: {e}")

    def place_order(self, side: str, amount: float, price: float):
        """下单"""
        try:
            # 获取当前价格
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = float(ticker['last'])
            
            # 检查是否会导致立即成交
            if side == 'bid':
                # 买单价格必须低于当前价格
                if price >= current_price:
                    logger.warning(f"跳过可能导致立即成交的买单: {amount} @ {price} (当前价格: {current_price})")
                    return None
            else:  # ask
                # 卖单价格必须高于当前价格
                if price <= current_price:
                    logger.warning(f"跳过可能导致立即成交的卖单: {amount} @ {price} (当前价格: {current_price})")
                    return None
                
            # 转换side参数为交易所需要的格式
            exchange_side = 'Bid' if side == 'bid' else 'Ask'
                
            # 创建订单参数
            order_params = {
                'symbol': self.symbol,
                'side': exchange_side,
                'type': 'limit',  # 使用驼峰命名法
                'amount': str(amount),  # 使用quantity而不是amount
                'price': str(price),
                'post_only': True,  # 使用驼峰命名法
                'time_in_force': 'GTC'
            }
            
            # 创建订单
            logger.info(f"创建订单参数: {order_params}")
            order = self.exchange.create_order(**order_params)
            
            # 创建订单信息并添加到订单管理器
            logger.info(f"订单信息: {order}")
            order_info = OrderInfo(
                order_id=order['id'],
                symbol=self.symbol,
                side=side,
                price=float(price),  # 确保是float类型
                amount=float(amount),  # 确保是float类型
                status='open',
                created_at=datetime.now()
            )
            logger.info(f"订单信息2: {order_info}")
            self.order_manager.add_order(order_info)
            
            logger.info(f"下单成功: {side} {float(amount)} {self.symbol} @ {float(price)}")  # 使用float类型进行日志输出
            return order
        except Exception as e:
            logger.error(f"下单错误: {e}")
            return None

    def cancel_all_orders(self):
        """取消所有订单"""
        try:
            open_orders = self.exchange.fetch_open_orders(self.symbol)
            if not open_orders:
                logger.info("没有未完成的订单")
                return
                
            for order in open_orders:
                if not order or 'id' not in order:
                    logger.warning("跳过无效订单")
                    continue
                    
                try:
                    # 使用正确的cancel_order方法
                    result = self.exchange.cancel_order(order['id'], self.symbol)
                    if result:
                        # 如果订单在我们的管理器中，更新状态
                        if order['id'] in self.order_manager.orders:
                            self.order_manager.update_order(order['id'], 'cancelled')
                            logger.info(f"已取消订单 {order['id']}")
                        else:
                            logger.info(f"已取消外部订单 {order['id']}")
                except Exception as e:
                    logger.error(f"取消订单 {order['id']} 失败: {e}")
                    continue
                    
            logger.info("订单取消操作完成")
        except Exception as e:
            logger.error(f"获取或取消订单时发生错误: {e}")

    def check_and_adjust_orders(self):
        """检查并调整订单"""
        try:
            # 获取当前价格和持仓
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = float(ticker['last'])
            
            # 获取账户余额
            balance = self.exchange.fetch_balance()
            base_currency, quote_currency = self.symbol.split('_')
            base_balance = float(balance.get(base_currency, {}).get('free', 0))
            
            # 检查是否触及止损或止盈
            if current_price <= self.stop_loss_price or current_price >= self.take_profit_price:
                logger.warning(f"触及止损/止盈价格，停止交易: {current_price}")
                self.cancel_all_orders()
                return False

            # 获取未完成订单
            open_orders = self.exchange.fetch_open_orders(self.symbol)
            
            # 更新订单状态
            for order in open_orders:
                if order['id'] in self.order_manager.orders:
                    if order['status'] == 'closed':
                        self.order_manager.update_order(
                            order['id'],
                            'closed',
                            float(order.get('average', 0)),
                            float(order.get('filled', 0))
                        )
            
            # 根据基础货币余额决定是否需要调整订单
            if base_balance == 0:
                # 没有基础货币，计算当前价格下方可以布置的买单数量
                possible_buy_orders = len([price for price in self.grid_prices if price < current_price])
                buy_orders = [order for order in open_orders if order['side'] == 'Bid']
                
                if len(buy_orders) < possible_buy_orders:
                    logger.info(f"{base_currency}余额为0，买单数量不足，重新布置网格。当前买单数量: {len(buy_orders)}，可布置买单数量: {possible_buy_orders}")
                    self.place_grid_orders()
            else:
                # 有基础货币，计算可用的卖单数量（考虑手续费）
                fee_rate = 0.003  # 0.1% 手续费率
                available_balance = base_balance * (1 - fee_rate)  # 考虑手续费后的可用余额
                possible_sell_orders = len([price for price in self.grid_prices if price > current_price])
                sell_orders = [order for order in open_orders if order['side'] == 'Ask']
                
                # 计算每个网格需要的数量
                grid_amount = self.get_order_amount(current_price)
                
                # 计算实际可以布置的卖单数量（考虑余额限制）
                max_possible_sell_orders = int(available_balance / grid_amount)
                actual_possible_sell_orders = min(possible_sell_orders, max_possible_sell_orders)
                
                if len(sell_orders) < actual_possible_sell_orders:
                    logger.info(f"卖单数量不足，重新布置网格。当前卖单数量: {len(sell_orders)}，可布置卖单数量: {actual_possible_sell_orders}，可用余额: {available_balance:.3f} {base_currency}")
                    self.place_grid_orders()
                
            # 打印订单汇总信息
            self.order_manager.print_order_summary()

            return True

        except Exception as e:
            logger.error(f"检查订单错误: {e}")
            return True

    def run(self):
        """运行网格交易"""
        logger.info("开始网格交易...")
        logger.info(f"交易对: {self.symbol}")
        logger.info(f"网格范围: {self.lower_price} - {self.upper_price}")
        logger.info(f"网格数量: {self.grid_number}")
        logger.info("按 Ctrl+C 可以安全退出程序")

        # 初始布置网格
        self.place_grid_orders()

        # 持续监控
        while True:
            try:
                if not self.check_and_adjust_orders():
                    break
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"运行错误: {e}")
                time.sleep(self.check_interval)

if __name__ == "__main__":
    trader = GridTrader()
    trader.run() 
