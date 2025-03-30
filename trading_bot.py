import json
import logging
from backpack_exchange import BackpackExchange
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """加载配置文件"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        raise

def main():
    # 加载配置
    config = load_config()
    
    # 初始化交易所
    exchange = BackpackExchange({
        'apiKey': config['apiKey'],
        'secret': config['secret']
    })
    
    try:
        # 遍历交易对
        for pair in config['trading_pairs']:
            symbol = pair['symbol']
            
            logger.info(f"正在处理交易对: {symbol}")
            
            # 获取市场行情
            ticker = exchange.fetch_ticker(symbol)
            logger.info(f"{symbol} 当前价格: {ticker['last']}")
            
            # 获取账户余额
            balance = exchange.fetch_balance()
            logger.info(f"账户余额: {balance}")
            
            # 创建订单
            order_params = config['order_params'].copy()
            order_params['symbol'] = symbol
            
            # 创建订单
            logger.info(f"创建订单: {order_params}")
            # order = exchange.create_order(**order_params)
            # logger.info(f"订单创建成功: {order}")
            
            # 等待一段时间
            # time.sleep(5)

            # 获取订单状态
            # order_status = exchange.fetch_order(114249091694002182, symbol, False)
            # logger.info(f"订单状态: {order_status}")

            # 获取最近的交易历史
            trades = exchange.fetch_my_trades(symbol)
            logger.info(f"最近的交易历史: {trades}")

            # 查找匹配的成交记录
            for trade in trades:
                if trade['symbol'] == symbol and trade['order'] == "114249091694002182":
                    logger.info(f"找到匹配的成交记录: {trade}")
                    break
            
            logger.info("-" * 50)
            
    except Exception as e:
        logger.error(f"发生错误: {e}")
        raise

if __name__ == "__main__":
    main() 