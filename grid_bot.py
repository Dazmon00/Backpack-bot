import time
import json
from loguru import logger
import os
from dotenv import load_dotenv, dotenv_values
from typing import Dict, List, Optional
from backpack_exchange import BackpackExchange
import sys
import logging
import asyncio
import requests

class GridBot:
    def __init__(self, config: Dict):
        self.exchange = BackpackExchange(config)
        self.symbol = config.get('symbol', 'ETH_USDC')
        self.grid_count = int(os.getenv('ETH_SPOT_GRID_NUMBER', 10))
        self.price_range = config.get('price_range', 0.1)  # 价格范围（百分比）
        self.total_investment = float(os.getenv('ETH_SPOT_TOTAL_INVESTMENT', 1000))  # 总投资金额(USDC)
        self.grid_prices = []  # 网格价格列表
        self.grid_states = {}  # 网格点状态字典
        self.active_orders = {}  # 活跃订单字典
        self.bought_eth = 0  # 已买入的ETH数量
        self.last_check_time = 0  # 上次检查时间
        self.check_interval = int(os.getenv('ETH_SPOT_CHECK_INTERVAL', 10))  # 检查间隔（秒）
        self.min_profit = float(os.getenv('ETH_SPOT_MIN_PROFIT', 0.5)) / 100  # 最小利润（百分比）
        self.stop_loss = config.get('stop_loss', 0.05)  # 止损比例（百分比）
        self.initial_price = None  # 初始价格
        self.initial_balance = {}  # 初始余额字典
        self.grid_positions = {}  # 网格点持仓记录
        self.maker_fee_rate = 0.0008  # 挂单费率 0.08%
        self.taker_fee_rate = 0.001  # 吃单费率 0.1%
        
        # 初始化网格
        self._initialize_grid()
        
    def _initialize_grid(self):
        """初始化网格"""
        try:
            # 从环境变量获取价格范围和网格数量
            price_min = float(os.getenv('ETH_SPOT_LOWER_PRICE'))
            price_max = float(os.getenv('ETH_SPOT_UPPER_PRICE'))
            grid_count = int(os.getenv('ETH_SPOT_GRID_NUMBER'))
            
            # 计算网格间距
            price_range = price_max - price_min
            grid_size = price_range / grid_count
            
            # 计算买入区间和卖出区间的网格数量
            buy_grid_count = grid_count // 3  # 买入区间占三分之一
            sell_grid_count = grid_count - buy_grid_count  # 卖出区间占三分之二
            
            # 计算买入区间和卖出区间的价格范围
            buy_price_max = price_min + (grid_size * buy_grid_count)
            
            # 计算每格交易量（基于USDC投资）
            self.grid_size = self.total_investment / grid_count  # 每格USDC投资量
            
            # 初始化网格状态和网格价格列表
            self.grid_states = {}
            self.grid_prices = []
            
            # 创建买入区间的网格
            for i in range(buy_grid_count):
                price = price_min + (grid_size * i)
                self.grid_prices.append(price)
                self.grid_states[price] = {
                    'state': 0,  # 0: 未持有, 1: 已持有
                    'buy_order_id': None,
                    'sell_order_id': None,
                    'buy_price': None,
                    'sell_price': None,
                    'buy_quantity': 0,
                    'sell_quantity': 0,
                    'position': 0,
                    'last_buy_time': 0,
                    'last_sell_time': 0
                }
            
            # 创建卖出区间的网格
            for i in range(sell_grid_count):
                price = buy_price_max + (grid_size * i)
                self.grid_prices.append(price)
                self.grid_states[price] = {
                    'state': 0,  # 0: 未持有, 1: 已持有
                    'buy_order_id': None,
                    'sell_order_id': None,
                    'buy_price': None,
                    'sell_price': None,
                    'buy_quantity': 0,
                    'sell_quantity': 0,
                    'position': 0,
                    'last_buy_time': 0,
                    'last_sell_time': 0
                }
            
            # 记录日志
            logger.info(f"网格初始化完成:")
            logger.info(f"价格范围: {price_min:.2f} - {price_max:.2f} (从.env文件读取)")
            logger.info(f"网格数量: {grid_count}")
            logger.info(f"买入区间: {price_min:.2f} - {buy_price_max:.2f} ({buy_grid_count}个网格)")
            logger.info(f"卖出区间: {buy_price_max:.2f} - {price_max:.2f} ({sell_grid_count}个网格)")
            logger.info(f"网格间距: {grid_size:.2f}")
            logger.info(f"总投资金额: {self.total_investment:.2f} USDC")
            logger.info(f"每格投资金额: {self.grid_size:.2f} USDC")
            
        except Exception as e:
            logger.error(f"初始化网格时出错: {str(e)}")
            raise

    def _check_orders(self):
        """检查订单状态"""
        try:
            # 获取当前时间
            current_time = time.time()

            # 检查每个网格点的订单
            for price, state in self.grid_states.items():
                # 检查买入订单
                if state['buy_order_id'] and state['buy_order_id'] is not None:  # 增加空值检查
                    try:
                        order = self.exchange.fetch_order(state['buy_order_id'], self.symbol)
                        if order:
                            if order['status'] == 'FILLED':
                                # 更新买入状态
                                state['state'] = 1  # 已持有
                                state['buy_price'] = float(order['price'])
                                state['buy_quantity'] = float(order['filled'])
                                state['position'] = float(order['filled'])
                                self.bought_eth += float(order['filled'])  # 更新已买入的ETH数量
                                
                                # 创建对应的卖出订单
                                sell_price = price * (1 + self.min_profit)
                                self._create_sell_order(price, float(order['filled']))
                                
                                # 记录日志
                                logger.info(f"买入订单已成交: 价格={price:.2f}, 数量={order['filled']}, 总买入: {self.bought_eth:.4f} ETH")
                                
                            elif order['status'] == 'PARTIALLY_FILLED':
                                # 更新部分成交状态
                                filled_amount = float(order['filled'])
                                state['buy_quantity'] = filled_amount
                                state['position'] = filled_amount
                                self.bought_eth += filled_amount  # 更新已买入的ETH数量
                                
                                # 记录日志
                                logger.info(f"买入订单部分成交: 价格={price:.2f}, 已成交数量={filled_amount}, 总数量={order['amount']}, 总买入: {self.bought_eth:.4f} ETH")
                                
                            elif order['status'] == 'CANCELLED':
                                # 清除买入订单记录
                                state['buy_order_id'] = None
                                state['state'] = 0  # 重置为未持有状态
                                logger.info(f"买入订单已取消: 价格={price:.2f}")
                                
                    except Exception as e:
                        if "请求的资源不存在" in str(e):
                            logger.info(f"买入订单不存在: {state['buy_order_id']}")
                            logger.info(f"如果订单不存在，可能是已经成交，尝试获取成交历")
                            # 如果订单不存在，可能是已经成交，尝试获取成交历史
                            try:
                                # 获取最近的成交历史
                                trades = self.exchange.fetch_my_trades(self.symbol, limit=100)
                                order_filled = False
                                
                                for trade in trades:
                                    if trade['order'] == state['buy_order_id']:
                                        # 找到对应的成交记录，更新状态
                                        state['state'] = 1  # 已持有
                                        state['buy_price'] = float(trade['price'])
                                        state['buy_quantity'] = float(trade['amount'])
                                        state['position'] = float(trade['amount'])
                                        self.bought_eth += float(trade['amount'])  # 更新已买入的ETH数量
                                        state['buy_order_id'] = None  # 清除订单ID
                                        order_filled = True
                                        
                                        # 创建对应的卖出订单
                                        sell_price = price * (1 + self.min_profit)
                                        self._create_sell_order(price, sell_price, float(trade['amount']))
                                        
                                        logger.info(f"从成交历史更新买入状态: 价格={trade['price']}, 数量={trade['amount']}, 总买入: {self.bought_eth:.4f} ETH")
                                        break
                                
                                if not order_filled:
                                    # 如果没有找到成交记录，说明订单可能被取消或删除
                                    logger.info(f"如果没有找到成交记录，说明订单可能被取消或删除")
                                    state['buy_order_id'] = None
                                    state['state'] = 0  # 重置为未持有状态
                                    logger.info(f"订单 {state['buy_order_id']} 未找到成交记录，重置状态")
                                    
                            except Exception as trade_error:
                                logger.error(f"获取成交历史时出错: {str(trade_error)}")
                        else:
                            logger.error(f"检查买入订单时出错: {str(e)}")
                
                # 检查卖出订单
                if state['sell_order_id'] and state['sell_order_id'] is not None:  # 增加空值检查
                    try:
                        order = self.exchange.fetch_order(state['sell_order_id'], self.symbol)
                        if order:
                            if order['status'] == 'FILLED':
                                # 更新卖出状态
                                state['state'] = 0  # 重置为未持有状态
                                state['sell_price'] = float(order['price'])
                                state['sell_quantity'] = float(order['filled'])
                                state['position'] = 0
                                self.bought_eth -= float(order['filled'])  # 更新已买入的ETH数量
                                
                                # 记录日志
                                logger.info(f"卖出订单已成交: 价格={order['price']}, 数量={order['filled']}, 总买入: {self.bought_eth:.4f} ETH")
                                
                            elif order['status'] == 'PARTIALLY_FILLED':
                                # 更新部分成交状态
                                filled_amount = float(order['filled'])
                                state['sell_quantity'] = filled_amount
                                state['position'] -= filled_amount
                                self.bought_eth -= filled_amount  # 更新已买入的ETH数量
                                
                                # 记录日志
                                logger.info(f"卖出订单部分成交: 价格={order['price']}, 已成交数量={filled_amount}, 总数量={order['amount']}, 总买入: {self.bought_eth:.4f} ETH")
                                
                            elif order['status'] == 'CANCELLED':
                                # 清除卖出订单记录
                                state['sell_order_id'] = None
                                logger.info(f"卖出订单已取消: 价格={order['price']}")
                                
                    except Exception as e:
                        if "请求的资源不存在" in str(e):
                            # 如果订单不存在，可能是已经成交，尝试获取成交历史
                            try:
                                # 获取最近的成交历史
                                trades = self.exchange.fetch_my_trades(self.symbol, limit=100)
                                order_filled = False
                                
                                for trade in trades:
                                    if trade['order'] == state['sell_order_id']:
                                        # 找到对应的成交记录，更新状态
                                        state['state'] = 0  # 重置为未持有状态
                                        state['sell_price'] = float(trade['price'])
                                        state['sell_quantity'] = float(trade['amount'])
                                        state['position'] = 0
                                        self.bought_eth -= float(trade['amount'])  # 更新已买入的ETH数量
                                        state['sell_order_id'] = None  # 清除订单ID
                                        order_filled = True
                                        
                                        logger.info(f"从成交历史更新卖出状态: 价格={trade['price']}, 数量={trade['amount']}, 总买入: {self.bought_eth:.4f} ETH")
                                        break
                                
                                if not order_filled:
                                    # 如果没有找到成交记录，说明订单可能被取消或删除
                                    state['sell_order_id'] = None
                                    logger.info(f"订单 {state['sell_order_id']} 未找到成交记录，重置状态")
                                    
                            except Exception as trade_error:
                                logger.error(f"获取成交历史时出错: {str(trade_error)}")
                        else:
                            logger.error(f"检查卖出订单时出错: {str(e)}")
            
            # 更新上次检查时间
            self.last_check_time = current_time
            
        except Exception as e:
            logger.error(f"检查订单状态时出错: {str(e)}")
            raise

    def _check_price(self):
        """检查价格并执行交易"""
        try:
            # 获取当前价格
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            # 获取账户余额
            balance = self.exchange.fetch_balance()
            usdc_balance = float(balance.get('USDC', {}).get('free', 0))
            eth_balance = float(balance.get('ETH', {}).get('free', 0))
            
            # 获取价格区间配置
            price_min = float(os.getenv('ETH_SPOT_LOWER_PRICE'))
            price_max = float(os.getenv('ETH_SPOT_UPPER_PRICE'))
            grid_count = int(os.getenv('ETH_SPOT_GRID_NUMBER'))
            
            # 计算买入区间和卖出区间的价格范围
            grid_size = (price_max - price_min) / grid_count
            buy_grid_count = grid_count // 3
            buy_price_max = price_min + (grid_size * buy_grid_count)
            
            # 计算总投入资金
            total_investment = self.total_investment
            current_investment = self.bought_eth * current_price
            
            logger.info(f"\n{'='*50}")
            logger.info(f"资金配置:")
            logger.info(f"计划总投入: {total_investment:.2f} USDC")
            logger.info(f"当前已投入: {current_investment:.2f} USDC")
            logger.info(f"剩余可用: {(total_investment - current_investment):.2f} USDC")
            logger.info(f"投入进度: {(current_investment / total_investment * 100):.2f}%")
            logger.info(f"\n价格区间配置:")
            logger.info(f"买入区间: {price_min:.2f} - {buy_price_max:.2f} ({buy_grid_count}个网格)")
            logger.info(f"卖出区间: {buy_price_max:.2f} - {price_max:.2f} ({grid_count - buy_grid_count}个网格)")
            logger.info(f"网格间距: {grid_size:.2f}")
            logger.info(f"当前价格: {current_price:.2f}")
            logger.info(f"账户余额: {eth_balance:.4f} ETH, {usdc_balance:.2f} USDC")
            logger.info(f"程序买入: {self.bought_eth:.4f} ETH")
            logger.info(f"每格投资金额: {self.grid_size:.2f} USDC")
            
            # 如果价格低于最低价格，只显示信息不操作
            if current_price < price_min:
                logger.info(f"\n当前价格 {current_price:.2f} 低于最低价格 {price_min:.2f}，等待价格回升")
                logger.info(f"{'='*50}\n")
                return
            
            # 找到当前价格所在的区间
            current_grid_index = None
            for i in range(len(self.grid_prices) - 1):
                if self.grid_prices[i] <= current_price <= self.grid_prices[i + 1]:
                    current_grid_index = i
                    break
            
            if current_grid_index is None:
                # 如果价格超出范围，找到最近的网格点
                if current_price > self.grid_prices[-1]:
                    current_grid_index = len(self.grid_prices) - 2
                else:
                    logger.info("\n当前价格不在任何网格区间内")
                    return
            
            # 获取当前区间的上下限价格
            lower_price = self.grid_prices[current_grid_index]
            upper_price = self.grid_prices[current_grid_index + 1]
            
            # 显示当前价格区间和相邻网格点
            logger.info(f"\n当前价格区间: {lower_price:.2f} - {current_price:.2f} - {upper_price:.2f}")
            
            # 显示所有网格点的状态和预计交易量
            logger.info("\n网格交易计划:")
            for i in range(len(self.grid_prices)):
                price = self.grid_prices[i]
                state = self.grid_states[price]
                status = "未持有" if state['state'] == 0 else "已持有" if state['state'] == 1 else "已卖出"
                price_diff = abs(current_price - price) / price * 100
                
                # 计算预期收益
                if state['state'] == 1:  # 已持有
                    next_price = self.grid_prices[i + 1] if i < len(self.grid_prices) - 1 else None
                    if next_price:
                        profit_percentage = (next_price - price) / price * 100
                        profit_usdc = (next_price - price) * state['position']
                        # 计算手续费（买入为吃单，卖出为挂单）
                        buy_fee = price * state['position'] * self.taker_fee_rate  # 买入为吃单
                        sell_fee = next_price * state['position'] * self.maker_fee_rate  # 卖出为挂单
                        total_fee = buy_fee + sell_fee
                        net_profit = profit_usdc - total_fee
                        net_profit_percentage = net_profit / (price * state['position']) * 100
                        
                        logger.info(f"网格 {i+1}: {price:.2f} - {status} | 持仓: {state['position']:.4f} ETH | 预计卖出: {next_price:.2f} | 毛收益: {profit_usdc:.2f} USDC ({profit_percentage:.2f}%) | 净收益: {net_profit:.2f} USDC ({net_profit_percentage:.2f}%)")
                else:
                    # 计算预计买入量
                    if price <= buy_price_max:  # 在买入区间
                        if price <= price_min + (buy_price_max - price_min) * 0.25:  # 最低25%区间
                            buy_amount = (self.grid_size * 1.5) / price  # 增加50%买入量
                            usdc_amount = self.grid_size * 1.5
                        elif price <= price_min + (buy_price_max - price_min) * 0.5:  # 25%-50%区间
                            buy_amount = (self.grid_size * 1.2) / price  # 增加20%买入量
                            usdc_amount = self.grid_size * 1.2
                        else:  # 50%-100%区间
                            buy_amount = self.grid_size / price  # 保持原买入量
                            usdc_amount = self.grid_size
                        
                        # 计算买入手续费
                        buy_fee = usdc_amount * self.taker_fee_rate
                        total_cost = usdc_amount + buy_fee
                        
                        logger.info(f"网格 {i+1}: {price:.2f} - {status} | 预计买入: {buy_amount:.4f} ETH | 投资金额: {usdc_amount:.2f} USDC | 买入手续费: {buy_fee:.2f} USDC | 总成本: {total_cost:.2f} USDC")
                    else:  # 在卖出区间
                        # 计算卖出比例
                        sell_range = price_max - buy_price_max
                        price_position = (price - buy_price_max) / sell_range
                        if price_position <= 0.33:  # 下三分之一区间
                            sell_ratio = 0.2  # 卖出20%
                        elif price_position <= 0.66:  # 中间三分之一区间
                            sell_ratio = 0.4  # 卖出40%
                        else:  # 上三分之一区间
                            sell_ratio = 0.6  # 卖出60%
                        
                        # 计算预计卖出量
                        expected_sell_amount = self.bought_eth * sell_ratio
                        expected_profit = (price - buy_price_max) * expected_sell_amount
                        sell_fee = price * expected_sell_amount * self.maker_fee_rate
                        net_profit = expected_profit - sell_fee
                        
                        logger.info(f"网格 {i+1}: {price:.2f} - {status} | 预计卖出: {expected_sell_amount:.4f} ETH (总持仓的{sell_ratio*100:.1f}%) | 预期收益: {expected_profit:.2f} USDC | 卖出手续费: {sell_fee:.2f} USDC | 净收益: {net_profit:.2f} USDC")
            
            # 检查当前区间的状态
            lower_state = self.grid_states[lower_price]
            upper_state = self.grid_states[upper_price]
            
            # 如果当前价格接近区间下限且未持有，创建买入订单
            price_diff = abs(current_price - lower_price) / lower_price
            if price_diff < 0.01 and lower_state['state'] == 0:  # 价格偏差小于1%
                # 检查是否在买入区间内
                if lower_price > buy_price_max:
                    logger.info(f"\n网格价格 {lower_price:.2f} - 不在买入区间内，跳过买入")
                    return
                    
                # 检查是否已有未完成的买入订单
                if lower_state['buy_order_id']:
                    # 计算预期收益
                    sell_fee = upper_price * (self.grid_size / lower_price) * self.maker_fee_rate  # 卖出为挂单
                    gross_profit = (upper_price - lower_price) * (self.grid_size / lower_price)
                    net_profit = gross_profit - sell_fee
                    logger.info(f"\n网格价格 {lower_price:.2f} - 已有买入订单 | 预计卖出: {upper_price:.2f} | 毛收益: {gross_profit:.2f} USDC ({(upper_price - lower_price) / lower_price * 100:.2f}%) | 卖出手续费(挂单): {sell_fee:.2f} USDC | 净收益: {net_profit:.2f} USDC ({net_profit / self.grid_size * 100:.2f}%)")
                    return
                    
                # 检查是否已有持仓
                if lower_state['position'] > 0:
                    logger.info(f"\n网格价格 {lower_price:.2f} - 已有持仓")
                    return
                    
                # 计算买入数量（基于USDC投资）
                quantity = self.grid_size / lower_price
                
                # 检查资金是否足够
                required_usdc = self.grid_size
                buy_fee = required_usdc * self.taker_fee_rate  # 买入为吃单
                total_cost = required_usdc + buy_fee
                
                if usdc_balance < total_cost:
                    logger.info(f"\n网格价格 {lower_price:.2f} - 资金不足 (需要: {total_cost:.2f} USDC)")
                    return
                    
                logger.info(f"\n创建买入订单: 价格: {lower_price:.2f} | 数量: {quantity:.4f} ETH | 所需资金: {required_usdc:.2f} USDC | 买入手续费(吃单): {buy_fee:.2f} USDC | 总成本: {total_cost:.2f} USDC | 预计卖出价: {upper_price:.2f}")
                
                # 计算预期收益（考虑手续费）
                sell_fee = upper_price * quantity * self.maker_fee_rate  # 卖出为挂单
                gross_profit = (upper_price - lower_price) * quantity
                total_fee = buy_fee + sell_fee
                net_profit = gross_profit - total_fee
                
                logger.info(f"预期收益: 毛收益: {gross_profit:.2f} USDC ({(upper_price - lower_price) / lower_price * 100:.2f}%) | 手续费: {total_fee:.2f} USDC | 净收益: {net_profit:.2f} USDC ({net_profit / total_cost * 100:.2f}%)")
                
                self._create_buy_order(lower_price, quantity)
            
            # 如果当前价格接近区间上限且已持有，创建卖出订单
            price_diff = abs(current_price - upper_price) / upper_price
            if price_diff < 0.01 and lower_state['state'] == 1:  # 价格偏差小于1%
                # 检查是否已有未完成的卖出订单
                if upper_state['sell_order_id']:
                    logger.info(f"\n网格价格 {upper_price:.2f} - 已有卖出订单")
                    return
                    
                # 检查是否有足够的持仓
                if lower_state['position'] < (self.grid_size / lower_price):
                    logger.info(f"\n网格价格 {upper_price:.2f} - 持仓不足")
                    return
                    
                logger.info(f"\n创建卖出订单: 价格: {upper_price:.2f} | 数量: {self.grid_size / lower_price:.4f} ETH")
                
                # 计算预期收益（考虑手续费）
                sell_fee = upper_price * (self.grid_size / lower_price) * self.maker_fee_rate  # 卖出为挂单
                gross_profit = (upper_price - lower_price) * (self.grid_size / lower_price)
                net_profit = gross_profit - sell_fee
                
                logger.info(f"预期收益: 毛收益: {gross_profit:.2f} USDC ({(upper_price - lower_price) / lower_price * 100:.2f}%) | 卖出手续费(挂单): {sell_fee:.2f} USDC | 净收益: {net_profit:.2f} USDC ({net_profit / (lower_price * (self.grid_size / lower_price)) * 100:.2f}%)")
                
                self._create_sell_order(lower_price, self.grid_size / lower_price)
            
            logger.info(f"{'='*50}\n")
            
        except Exception as e:
            logger.error(f"检查价格时出错: {str(e)}")
            raise

    def _create_buy_order(self, price: float, quantity: float):
        """创建买入订单"""
        try:
            # 检查网格点状态
            state = self.grid_states[price]
            
            # 检查是否可以买入
            if state['state'] != 0:  # 状态不为未持有
                return
            
            # 检查是否有未完成的买入订单
            if state['buy_order_id']:
                return
            
            # 检查持仓
            if state['position'] > 0:
                return
            
            # 获取当前市场价格
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            # 如果价格太接近当前市场价格，调整价格
            price_diff = abs(current_price - price) / current_price
            if price_diff < 0.001:  # 如果价格偏差小于0.1%
                # 将价格调整为当前价格的0.1%以下
                price = current_price * 0.999
            
            # 对价格和数量进行四舍五入处理
            rounded_price = round(price, 2)
            rounded_quantity = round(quantity, 4)  # ETH数量保留4位小数
            
            # 根据价格区间调整买入量
            price_min = float(os.getenv('ETH_SPOT_LOWER_PRICE'))
            price_max = float(os.getenv('ETH_SPOT_UPPER_PRICE'))
            grid_count = int(os.getenv('ETH_SPOT_GRID_NUMBER'))
            
            # 计算买入区间的最大价格
            buy_price_max = price_min + ((price_max - price_min) * (grid_count // 3) / grid_count)
            
            # 根据价格位置调整买入量
            if price <= price_min + (buy_price_max - price_min) * 0.25:  # 最低25%区间
                adjusted_quantity = round(rounded_quantity * 1.5, 4)  # 增加50%买入量
            elif price <= price_min + (buy_price_max - price_min) * 0.5:  # 25%-50%区间
                adjusted_quantity = round(rounded_quantity * 1.2, 4)  # 增加20%买入量
            else:  # 50%-100%区间
                adjusted_quantity = rounded_quantity  # 保持原买入量
            
            # 创建买入订单
            order = self.exchange.create_order(
                symbol=self.symbol,
                type='limit',
                side='buy',
                amount=adjusted_quantity,
                price=rounded_price,
                post_only=True,
                time_in_force='GTC'
            )
            
            # 更新网格点状态
            state['buy_order_id'] = order['id']
            state['last_buy_time'] = time.time()
            
            logger.info(f"买入订单创建成功 -> ID: {order['id']}, 价格: {rounded_price:.2f}, 数量: {adjusted_quantity:.4f}")
            
        except Exception as e:
            logger.error(f"创建买入订单时出错: {str(e)}")
            raise

    def _create_sell_order(self, price: float, quantity: float):
        """创建卖出订单"""
        try:
            # 检查网格点状态
            state = self.grid_states[price]
            
            # 检查是否可以卖出
            if state['state'] != 1:  # 状态不为已持有
                return
            
            # 检查是否有未完成的卖出订单
            if state['sell_order_id']:
                return
            
            # 检查持仓
            if state['position'] <= 0:
                return
            
            # 获取当前市场价格
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            # 如果价格太接近当前市场价格，调整价格
            price_diff = abs(current_price - price) / current_price
            if price_diff < 0.001:  # 如果价格偏差小于0.1%
                # 将价格调整为当前价格的0.1%以上
                price = current_price * 1.001
            
            # 对价格和数量进行四舍五入处理
            rounded_price = round(price, 2)
            rounded_quantity = round(quantity, 4)  # ETH数量保留4位小数
            
            # 根据价格区间调整卖出比例
            price_min = float(os.getenv('ETH_SPOT_LOWER_PRICE'))
            price_max = float(os.getenv('ETH_SPOT_UPPER_PRICE'))
            grid_count = int(os.getenv('ETH_SPOT_GRID_NUMBER'))
            
            # 计算买入区间的最大价格
            buy_price_max = price_min + ((price_max - price_min) * (grid_count // 3) / grid_count)
            
            # 计算价格在卖出区间的位置
            sell_range = price_max - buy_price_max
            price_position = (price - buy_price_max) / sell_range
            
            # 根据价格位置调整卖出比例
            if price_position <= 0.33:  # 下三分之一区间
                sell_ratio = 0.2  # 卖出20%
            elif price_position <= 0.66:  # 中间三分之一区间
                sell_ratio = 0.4  # 卖出40%
            else:  # 上三分之一区间
                sell_ratio = 0.6  # 卖出60%
            
            # 计算实际卖出数量
            adjusted_quantity = round(rounded_quantity * sell_ratio, 4)
            
            # 创建卖出订单
            order = self.exchange.create_order(
                symbol=self.symbol,
                type='limit',
                side='sell',
                amount=adjusted_quantity,
                price=rounded_price,
                post_only=True,
                time_in_force='GTC'
            )
            
            # 更新网格点状态
            state['sell_order_id'] = order['id']
            state['last_sell_time'] = time.time()
            
            logger.info(f"卖出订单创建成功 -> ID: {order['id']}, 价格: {rounded_price:.2f}, 数量: {adjusted_quantity:.4f}, 卖出比例: {sell_ratio*100}%")
            
        except Exception as e:
            logger.error(f"创建卖出订单时出错: {str(e)}")
            raise

    def run(self):
        """运行网格交易机器人"""
        try:
            logger.info("开始运行网格交易机器人")
            last_price_check = 0  # 上次价格检查时间
            
            while True:
                try:
                    current_time = time.time()
                    
                    # 检查订单状态（频繁检查）
                    self._check_orders()
                    
                    # 检查价格（降低频率，避免过多API调用）
                    if current_time - last_price_check >= self.check_interval:
                        self._check_price()
                        last_price_check = current_time
                        logger.info("执行价格检查")
                    
                    # 等待下一次检查
                    time.sleep(1)  # 降低订单检查频率，避免过多API调用
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"网络请求错误: {str(e)}")
                    time.sleep(self.check_interval * 2)  # 网络错误时等待更长时间
                except ValueError as e:
                    logger.error(f"数据验证错误: {str(e)}")
                    time.sleep(self.check_interval)
                except Exception as e:
                    logger.error(f"运行过程中出错: {str(e)}")
                    time.sleep(self.check_interval)
                    
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在关闭...")
            self.stop()
        except Exception as e:
            logger.error(f"机器人运行出错: {str(e)}")
            raise

    def load_config(self):
        """加载配置"""
        try:
            # 加载环境变量
            env_vars = os.environ
            
            # 加载全局配置
            self.error_cooldown = int(env_vars.get('ERROR_COOLDOWN', 60))
            self.max_active_pairs = int(env_vars.get('MAX_ACTIVE_PAIRS', 2))
            self.check_interval = int(env_vars.get('CHECK_INTERVAL', 10))
            
            # 设置日志级别
            log_level = env_vars.get('LOG_LEVEL', 'INFO')
            self.setup_logging()
            
            # 获取初始余额
            balance = self.exchange.fetch_balance()
            for symbol in ['ETH', 'USDC']:
                self.initial_balance[symbol] = float(balance.get(symbol, {}).get('free', 0))
                logger.info(f"初始 {symbol} 余额: {self.initial_balance[symbol]}")
            
            # 加载 BTC-USDC 现货配置
            if env_vars.get('BTC_SPOT_ENABLED', 'false').lower() == 'true':
                self.grid_configs['BTC_USDC'] = {
                    'symbol': env_vars.get('BTC_SPOT_SYMBOL', 'BTC_USDC'),
                    'upper_price': float(env_vars.get('BTC_SPOT_UPPER_PRICE', 70000)),
                    'lower_price': float(env_vars.get('BTC_SPOT_LOWER_PRICE', 60000)),
                    'grid_number': int(env_vars.get('BTC_SPOT_GRID_NUMBER', 10)),
                    'grid_size': float(env_vars.get('BTC_SPOT_GRID_SIZE', 0.001)),
                    'check_interval': int(env_vars.get('BTC_SPOT_CHECK_INTERVAL', 10)),
                    'min_profit_percentage': float(env_vars.get('BTC_SPOT_MIN_PROFIT', 0.5)),
                    'is_futures': False
                }
            
            # 加载 BTC-USDC 合约配置
            if env_vars.get('BTC_FUTURES_ENABLED', 'false').lower() == 'true':
                self.grid_configs['BTC_USDC'] = {
                    'symbol': env_vars.get('BTC_FUTURES_SYMBOL', 'BTC_USDC'),
                    'upper_price': float(env_vars.get('BTC_FUTURES_UPPER_PRICE', 70000)),
                    'lower_price': float(env_vars.get('BTC_FUTURES_LOWER_PRICE', 60000)),
                    'grid_number': int(env_vars.get('BTC_FUTURES_GRID_NUMBER', 10)),
                    'grid_size': float(env_vars.get('BTC_FUTURES_GRID_SIZE', 0.001)),
                    'check_interval': int(env_vars.get('BTC_FUTURES_CHECK_INTERVAL', 10)),
                    'min_profit_percentage': float(env_vars.get('BTC_FUTURES_MIN_PROFIT', 0.5)),
                    'is_futures': True,
                    'leverage': int(env_vars.get('BTC_FUTURES_LEVERAGE', 2)),
                    'margin_type': env_vars.get('BTC_FUTURES_MARGIN_TYPE', 'ISOLATED')
                }
            
            # 加载 ETH-USDC 现货配置
            if env_vars.get('ETH_SPOT_ENABLED', 'false').lower() == 'true':
                self.grid_configs['ETH_USDC'] = {
                    'symbol': env_vars.get('ETH_SPOT_SYMBOL', 'ETH_USDC'),
                    'upper_price': float(env_vars.get('ETH_SPOT_UPPER_PRICE', 4000)),
                    'lower_price': float(env_vars.get('ETH_SPOT_LOWER_PRICE', 3500)),
                    'grid_number': int(env_vars.get('ETH_SPOT_GRID_NUMBER', 10)),
                    'grid_size': float(env_vars.get('ETH_SPOT_GRID_SIZE', 0.005)),
                    'check_interval': int(env_vars.get('ETH_SPOT_CHECK_INTERVAL', 10)),
                    'min_profit_percentage': float(env_vars.get('ETH_SPOT_MIN_PROFIT', 0.5)),
                    'is_futures': False
                }
            
            # 加载 ETH-USDC 合约配置
            if env_vars.get('ETH_FUTURES_ENABLED', 'false').lower() == 'true':
                self.grid_configs['ETH_USDC'] = {
                    'symbol': env_vars.get('ETH_FUTURES_SYMBOL', 'ETH_USDC'),
                    'upper_price': float(env_vars.get('ETH_FUTURES_UPPER_PRICE', 4000)),
                    'lower_price': float(env_vars.get('ETH_FUTURES_LOWER_PRICE', 3500)),
                    'grid_number': int(env_vars.get('ETH_FUTURES_GRID_NUMBER', 10)),
                    'grid_size': float(env_vars.get('ETH_FUTURES_GRID_SIZE', 0.005)),
                    'check_interval': int(env_vars.get('ETH_FUTURES_CHECK_INTERVAL', 10)),
                    'min_profit_percentage': float(env_vars.get('ETH_FUTURES_MIN_PROFIT', 0.5)),
                    'is_futures': True,
                    'leverage': int(env_vars.get('ETH_FUTURES_LEVERAGE', 2)),
                    'margin_type': env_vars.get('ETH_FUTURES_MARGIN_TYPE', 'ISOLATED')
                }
            
            # 验证配置
            if not self.grid_configs:
                raise ValueError("没有启用任何交易对")
            
            if len(self.grid_configs) > self.max_active_pairs:
                raise ValueError(f"启用的交易对数量({len(self.grid_configs)})超过最大限制({self.max_active_pairs})")
            
            # 初始化每个交易对的买入ETH记录
            self.bought_eth = {symbol: 0 for symbol in self.grid_configs}
            
            logger.info("配置加载成功")
            logger.info(f"启用的交易对: {', '.join(self.grid_configs.keys())}")
            
        except Exception as e:
            logger.error(f"加载配置时出错: {str(e)}")
            raise

    def _calculate_grid_levels(self, symbol: str):
        """计算网格价格水平"""
        if symbol not in self.grid_configs:
            raise ValueError(f"Configuration not found for {symbol}")

        config = self.grid_configs[symbol]
        upper_price = config['upper_price']
        lower_price = config['lower_price']
        grid_number = config['grid_number']
        
        # 使用对数间隔计算网格价格,使网格更密集
        price_step = (upper_price - lower_price) / grid_number
        self.grid_levels[symbol] = [lower_price + i * price_step for i in range(grid_number + 1)]
        
        logger.info(f"Calculated {len(self.grid_levels[symbol])} grid levels for {symbol}")

    def _calculate_grid_prices(self, current_price: float, upper_price: float, lower_price: float, grid_number: int) -> List[float]:
        """
        计算网格价格
        :param current_price: 当前价格
        :param upper_price: 上限价格
        :param lower_price: 下限价格
        :param grid_number: 网格数量
        :return: 网格价格列表
        """
        # 计算价格间隔
        price_step = (upper_price - lower_price) / (grid_number - 1)
        
        # 生成网格价格列表
        grid_prices = []
        for i in range(grid_number):
            price = lower_price + (price_step * i)
            grid_prices.append(round(price, 2))  # 保留2位小数
        
        # 确保当前价格在网格范围内
        if current_price < lower_price:
            current_price = lower_price
        elif current_price > upper_price:
            current_price = upper_price
            
        # 将当前价格插入到合适的位置
        for i in range(len(grid_prices) - 1):
            if grid_prices[i] <= current_price <= grid_prices[i + 1]:
                grid_prices.insert(i + 1, current_price)
                break
        
        logger.info(f"网格价格列表: {grid_prices}")
        return grid_prices

    async def _check_and_execute_trades(self, symbol: str, config: Dict, current_price: float) -> None:
        """检查并执行交易"""
        try:
            # 计算网格价格
            grid_prices = self._calculate_grid_prices(
                current_price,
                float(config['upper_price']),
                float(config['lower_price']),
                int(config['grid_number'])
            )
            
            # 获取当前订单
            logger.info(f"获取当前订单: {symbol}")
            orders = self._get_current_orders(symbol)
            
            # 执行交易
            logger.info(f"执行交易: {symbol}")
            await self._execute_trades(symbol, current_price, grid_prices, orders, config)
            
        except Exception as e:
            logger.error(f"检查交易时出错: {str(e)}")
            raise

    def start(self):
        """启动网格交易"""
        if not self.grid_configs:
            raise ValueError("No trading pairs configured")

        logger.info(f"Starting grid trading for {len(self.grid_configs)} pairs")
        
        while True:
            try:
                # 创建事件循环
                loop = asyncio.get_event_loop()
                
                # 遍历所有配置的交易对
                for symbol in self.grid_configs:
                    # 获取当前市场价格
                    config = self.grid_configs[symbol]
                    ticker = self.exchange.fetch_ticker(symbol, config['is_futures'])
                    current_price = ticker['last']
                    
                    # 检查并执行交易
                    logger.info(f"检查并执行交易: {symbol}")
                    loop.run_until_complete(self._check_and_execute_trades(symbol, config, current_price))
                    
                    # 检查订单状态
                    logger.info(f"检查订单状态: {symbol}")
                    self._check_orders()
                
                # 等待下一次检查
                time.sleep(min(config['check_interval'] for config in self.grid_configs.values()))
                
            except Exception as e:
                current_time = time.time()
                if current_time - self.last_error_time > self.error_cooldown:
                    logger.error(f"Error in main loop: {str(e)}")
                    self.last_error_time = current_time
                time.sleep(10)

    def stop(self):
        """停止网格交易并取消所有订单"""
        try:
            logger.info("开始取消所有未完成订单...")
            
            # 遍历所有网格点状态
            for price, state in self.grid_states.items():
                # 取消买入订单
                if state['buy_order_id']:
                    try:
                        self.exchange.cancel_order(state['buy_order_id'], self.symbol)
                        logger.info(f"已取消买入订单: {state['buy_order_id']}")
                    except Exception as e:
                        logger.error(f"取消买入订单失败: {str(e)}")
                
                # 取消卖出订单
                if state['sell_order_id']:
                    try:
                        self.exchange.cancel_order(state['sell_order_id'], self.symbol)
                        logger.info(f"已取消卖出订单: {state['sell_order_id']}")
                    except Exception as e:
                        logger.error(f"取消卖出订单失败: {str(e)}")
            
            logger.info("所有订单已取消，机器人已停止")
            
        except Exception as e:
            logger.error(f"停止机器人时出错: {str(e)}")
            raise

    def _get_current_orders(self, symbol: str) -> List[Dict]:
        """
        获取当前交易对的所有活动订单
        :param symbol: 交易对
        :return: 订单列表
        """
        orders = []
        # 创建订单键的副本以避免迭代时修改
        order_keys = [key for key in self.active_orders.keys() if key.startswith(symbol)]
        
        for order_key in order_keys:
            try:
                order = self.active_orders[order_key]
                # 获取最新订单状态
                updated_order = self.exchange.fetch_order(
                    order['id'],
                    symbol,
                    self.grid_configs[symbol]['is_futures']
                )
                
                # 检查订单状态
                if updated_order and updated_order.get('status') in ['FILLED', 'CANCELLED', 'EXPIRED']:
                    logger.info(f"订单 {order['id']} 状态为 {updated_order.get('status')}，从活动订单中移除")
                    if order_key in self.active_orders:
                        del self.active_orders[order_key]
                    continue
                    
                orders.append(updated_order)
            except Exception as e:
                if "请求的资源不存在" in str(e):
                    logger.info(f"订单 {order.get('id', 'unknown')} 已不存在，从活动订单中移除")
                    if order_key in self.active_orders:
                        del self.active_orders[order_key]
                else:
                    logger.error(f"获取订单 {order.get('id', 'unknown')} 状态时出错: {str(e)}")
                continue
                
        return orders

    async def _execute_trades(self, symbol: str, current_price: float, grid_prices: List[float], orders: List[Dict], config: Dict) -> None:
        """
        执行网格交易
        :param symbol: 交易对
        :param current_price: 当前价格
        :param grid_prices: 网格价格列表
        :param orders: 当前订单列表
        :param config: 交易配置
        """
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"开始执行网格交易 - {symbol}")
            logger.info(f"当前价格: {current_price}")
            logger.info(f"网格价格列表: {grid_prices}")
            
            # 获取账户余额
            balance = self.exchange.fetch_balance()
            usdc_balance = float(balance.get('USDC', {}).get('free', 0))
            eth_balance = float(balance.get('ETH', {}).get('free', 0))
            logger.info(f"当前USDC余额: {usdc_balance}")
            logger.info(f"当前ETH余额: {eth_balance}")
            logger.info(f"程序运行期间买入的ETH: {self.bought_eth[symbol]}")
            await asyncio.sleep(5)  # 睡眠5秒
            
            # 计算每个网格需要的资金
            grid_amount = config['grid_size']
            grid_cost = grid_amount * current_price
            logger.info(f"每个网格所需资金: {grid_cost} USDC")
            await asyncio.sleep(5)  # 睡眠5秒
            
            # 检查资金是否足够
            if usdc_balance < grid_cost:
                logger.warning(f"资金不足，无法创建新订单。需要: {grid_cost} USDC, 可用: {usdc_balance} USDC")
                logger.info(f"{'='*50}\n")
                return
            
            # 遍历网格价格
            for i in range(len(grid_prices) - 1):
                lower_price = grid_prices[i]
                upper_price = grid_prices[i + 1]
                
                # 检查是否在价格区间内
                if lower_price <= current_price <= upper_price:
                    logger.info(f"当前价格 {current_price} 在区间内")
                    
                    # 计算预期利润
                    expected_profit = (upper_price - lower_price) / lower_price * 100
                    logger.info(f"预期利润率: {expected_profit:.2f}%")
                    logger.info(f"最小要求利润率: {config['min_profit_percentage']}%")
                    
                    # 只有当预期利润大于最小利润率时才创建订单
                    if expected_profit >= config['min_profit_percentage']:
                        logger.info(f"预期利润率满足要求，准备创建订单")
                        
                        # 检查该价格区间是否已有未完成的订单
                        has_pending_orders = False
                        for order_key in self.active_orders:
                            if order_key.startswith(symbol) and order_key.endswith(f"_{i}") or order_key.endswith(f"_{i+1}"):
                                has_pending_orders = True
                                logger.info(f"价格区间 {lower_price} - {upper_price} 已有未完成的订单，跳过创建")
                                break
                        
                        if has_pending_orders:
                            continue
                        
                        # 创建买单
                        buy_order_key = f"{symbol}_{i}"
                        if buy_order_key not in self.active_orders:
                            logger.info(f"检查买单 {buy_order_key}")
                            try:
                                # 计算买单所需资金
                                buy_cost = grid_amount * lower_price
                                if usdc_balance < buy_cost:
                                    logger.warning(f"资金不足，无法创建买单。需要: {buy_cost} USDC, 可用: {usdc_balance} USDC")
                                    continue
                                
                                logger.info(f"创建买单:")
                                logger.info(f"交易对: {symbol}")
                                logger.info(f"价格: {lower_price}")
                                logger.info(f"数量: {grid_amount}")
                                logger.info(f"所需资金: {buy_cost} USDC")
                                logger.info(f"类型: {'合约' if config['is_futures'] else '现货'}")
                                if config['is_futures']:
                                    logger.info(f"杠杆: {config.get('leverage')}")
                                    logger.info(f"保证金类型: {config.get('margin_type')}")
                                
                                buy_order = self.exchange.create_order(
                                    symbol=symbol,
                                    type='limit',
                                    side='buy',
                                    amount=grid_amount,
                                    price=lower_price,
                                    is_futures=config['is_futures'],
                                    leverage=config.get('leverage'),
                                    margin_type=config.get('margin_type')
                                )
                                self.active_orders[buy_order_key] = buy_order
                                logger.info(f"创建买单成功: {buy_order}")
                            except Exception as e:
                                logger.error(f"创建买单失败 {symbol}: {str(e)}")
                        else:
                            logger.info(f"买单 {buy_order_key} 已存在，跳过创建")
                        
                        # 创建卖单
                        sell_order_key = f"{symbol}_{i+1}"
                        if sell_order_key not in self.active_orders:
                            logger.info(f"检查卖单 {sell_order_key}")
                            try:
                                # 检查程序运行期间买入的ETH余额
                                if self.bought_eth[symbol] < grid_amount:
                                    logger.warning(f"程序运行期间买入的ETH不足，无法创建卖单。需要: {grid_amount} ETH, 可用: {self.bought_eth[symbol]} ETH")
                                    continue

                                logger.info(f"创建卖单:")
                                logger.info(f"交易对: {symbol}")
                                logger.info(f"价格: {upper_price}")
                                logger.info(f"数量: {grid_amount}")
                                logger.info(f"预期收益: {(upper_price - lower_price) * grid_amount} USDC")
                                logger.info(f"类型: {'合约' if config['is_futures'] else '现货'}")
                                if config['is_futures']:
                                    logger.info(f"杠杆: {config.get('leverage')}")
                                    logger.info(f"保证金类型: {config.get('margin_type')}")
                                
                                sell_order = self.exchange.create_order(
                                    symbol=symbol,
                                    type='limit',
                                    side='sell',
                                    amount=grid_amount,
                                    price=upper_price,
                                    is_futures=config['is_futures'],
                                    leverage=config.get('leverage'),
                                    margin_type=config.get('margin_type')
                                )
                                self.active_orders[sell_order_key] = sell_order
                                logger.info(f"创建卖单成功: {sell_order}")
                            except Exception as e:
                                logger.error(f"创建卖单失败 {symbol}: {str(e)}")
                        else:
                            logger.info(f"卖单 {sell_order_key} 已存在，跳过创建")
                    else:
                        logger.info(f"预期利润率 {expected_profit:.2f}% 不满足最小要求 {config['min_profit_percentage']}%，跳过创建订单")
                else:
                    logger.info(f"当前价格 {current_price} 不在区间内，跳过创建订单")
        
            # 更新当前价格区间
            self.current_price_range = (grid_prices[0], grid_prices[-1])
            logger.info(f"\n当前价格区间: {self.current_price_range[0]} - {self.current_price_range[1]}")
            await asyncio.sleep(5)  # 睡眠5秒
            
            # 计算预期利润率
            expected_profit_rate = (self.current_price_range[1] - self.current_price_range[0]) / self.current_price_range[0]
            logger.info(f"预期利润率: {expected_profit_rate:.2%}")
            logger.info(f"最小要求利润率: {config['min_profit_percentage']:.2%}")
            await asyncio.sleep(5)  # 睡眠5秒
            
            logger.info(f"{'='*50}\n")

        except Exception as e:
            logger.error(f"执行交易时出错: {str(e)}")
            raise

    def setup_logging(self):
        """配置日志"""
        # 从环境变量获取日志级别
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 配置控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 配置文件处理器
        file_handler = logging.FileHandler('grid_bot.log')
        file_handler.setFormatter(formatter)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        
        # 设置其他模块的日志级别
        logging.getLogger('backpack_exchange').setLevel(log_level)
        logging.getLogger('urllib3').setLevel(log_level)
        logging.getLogger('requests').setLevel(log_level)
        
        logger.info(f"日志级别设置为: {log_level}")

def main():
    # 加载环境变量
    load_dotenv()
    
    # 获取API凭证
    api_key = os.getenv('BACKPACK_API_KEY')
    api_secret = os.getenv('BACKPACK_API_SECRET')
    
    if not api_key or not api_secret:
        raise ValueError("Backpack API credentials not found in environment variables")
    
    # 创建配置字典
    config = {
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'symbol': 'ETH_USDC',
        'grid_count': 10,
        'price_range': 0.1,
        'total_investment': 1000,
        'check_interval': 1,
        'min_profit': 0.02,
        'stop_loss': 0.05,
        'fee_rate': 0.001
    }
    
    # 创建网格机器人实例
    bot = GridBot(config)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Stopping grid bot...")
        bot.stop()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        bot.stop()

if __name__ == "__main__":
    main() 