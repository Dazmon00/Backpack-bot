# Backpack Grid Trading Bot

这是一个基于 Backpack Exchange 的网格交易机器人，支持等差和等比网格策略，具有自动下单、止盈止损等功能。

## 功能特点

- 支持等差和等比网格策略
- 自动计算网格价格和订单数量
- 实时监控订单状态
- 支持止盈止损
- 自动检查账户余额
- 支持最小订单数量限制
- 支持最大订单数量限制
- 支持 post-only 模式
- 支持自定义检查间隔
- 优雅的退出机制（支持 Ctrl+C）

## 环境要求

- Python 3.7+
- pip

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

在项目根目录创建 `.env` 文件，配置以下参数：

```env
# API配置
API_KEY=your_api_key
API_SECRET=your_api_secret

# 交易配置
SYMBOL=ETH_USDC  # 交易对
GRID_TYPE=arithmetic  # 网格类型：arithmetic(等差) 或 geometric(等比)
UPPER_PRICE=2000  # 网格上限价格
LOWER_PRICE=1800  # 网格下限价格
GRID_NUMBER=10  # 网格数量
INVESTMENT=1000  # 总投资金额(USDC)
MIN_ORDER_SIZE=0.001  # 最小订单数量
MAX_ORDERS=20  # 最大订单数量

# 风险控制
STOP_LOSS_PRICE=1700  # 止损价格
TAKE_PROFIT_PRICE=2100  # 止盈价格
POST_ONLY=true  # 是否只挂单不吃单
TIME_IN_FORCE=GTC  # 订单有效期：GTC(一直有效) 或 IOC(立即成交或取消)

# 系统配置
CHECK_INTERVAL=60  # 检查间隔(秒)
LOG_LEVEL=INFO  # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 使用说明

1. 配置环境变量：
   - 复制 `.env.example` 为 `.env`
   - 填写您的 API 密钥和其他配置参数

2. 运行机器人：
   ```bash
   python grid_trader.py
   ```

3. 监控运行状态：
   - 程序会实时显示网格信息和订单状态
   - 可以通过日志查看详细信息

4. 安全退出：
   - 按 Ctrl+C 可以安全退出程序
   - 程序会自动取消所有未完成订单

## 网格策略说明

### 等差网格
- 价格区间均匀分布
- 适合价格波动较小的市场
- 每个网格的收益相同

### 等比网格
- 价格区间按比例分布
- 适合价格波动较大的市场
- 每个网格的收益率相同

## 风险提示

1. 请确保理解网格交易的风险
2. 建议先用小额资金测试
3. 请妥善保管 API 密钥
4. 建议设置合理的止盈止损价格
5. 注意监控账户余额

## 常见问题

1. 如何修改网格参数？
   - 直接修改 `.env` 文件中的相应参数
   - 修改后需要重启程序

2. 如何查看交易记录？
   - 程序会实时显示订单状态
   - 可以在 Backpack Exchange 官网查看详细记录

3. 如何处理程序异常退出？
   - 程序会自动取消所有未完成订单
   - 重新启动程序即可继续交易
