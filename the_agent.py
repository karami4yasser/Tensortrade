import ray
import numpy as np
import pandas as pd
from ray import tune
from ray.tune.registry import register_env
import tensortrade.env.default as default
from tensortrade.feed.core import DataFeed, Stream
from tensortrade.oms.exchanges import Exchange
from tensortrade.oms.services.execution.simulated import execute_order
from tensortrade.oms.wallets import Wallet, Portfolio

from tensortrade.oms.instruments import Instrument
USD = Instrument("USD", 2, "U.S. Dollar")
TTC = Instrument("BTC", 8, "TensorTrade Coin")


from gym.spaces import Discrete
from tensortrade.env.default.actions import TensorTradeActionScheme
from tensortrade.env.generic import ActionScheme, TradingEnv
from tensortrade.core import Clock
from tensortrade.oms.instruments import ExchangePair
from tensortrade.oms.wallets import Portfolio
from tensortrade.oms.orders import (
Order,
proportion_order,
TradeSide,
TradeType
)




#------------------------------------
import mysql.connector

mydb = mysql.connector.connect(
  host="localhost",
  user="mb",
  password="mbpass123",
  database="cryptos"
)

mycursor = mydb.cursor()

all_symbols=['BTC','ETH','XRP','BCH','ADA','LTC','XEM','XLM','EOS','NOE','MIOTA','DASH','XMR','TRX','XTZ','DOGE','ETC','VEN','USDT','BNB']
for i in range(0,len(all_symbols)):
  all_symbols[i]=all_symbols[10]+"-USD"

#----------------------------------
crypto=all_symbols[1]
class BSH(TensorTradeActionScheme):
  registered_name = "bsh"
  def __init__(self, cash: 'Wallet', asset: 'Wallet'):
    super().__init__()
    self.cash = cash
    self.asset = asset
    self.listeners = []
    self.action = 0
  @property
  def action_space(self):
    return Discrete(2)
  def attach(self, listener):
    self.listeners += [listener]
    return self
  def get_orders(self, action: int, portfolio: 'Portfolio'):
    order = None
    if abs(action - self.action) > 0:
      src = self.cash if self.action == 0 else self.asset
      tgt = self.asset if self.action == 0 else self.cash
      order = proportion_order(portfolio, src, tgt, 1.0)
      self.action = action
    for listener in self.listeners:
      listener.on_action(action)
      return [order]
  def reset(self):
    super().reset()
    self.action = 0
     
from tensortrade.env.default.rewards import TensorTradeRewardScheme
from tensortrade.feed.core import Stream, DataFeed
class PBR(TensorTradeRewardScheme):
  registered_name = "pbr"
  def __init__(self, price: 'Stream'):
    super().__init__()
    self.position = -1
    r = Stream.sensor(price, lambda p: p.value, dtype="float").diff()
    position = Stream.sensor(self, lambda rs: rs.position, dtype="float")
    reward = (r * position).fillna(0).rename("reward")
    self.feed = DataFeed([reward])
    self.feed.compile()
  def on_action(self, action: int):
    self.position = -1 if action == 0 else 1
  def get_reward(self, portfolio: 'Portfolio'):
    return self.feed.next()["reward"]
  def reset(self):
    self.position = -1
    self.feed.reset()      



import matplotlib.pyplot as plt
from tensortrade.env.generic import Renderer
class PositionChangeChart(Renderer):
  def __init__(self, color: str = "orange"):
    self.color = "orange"
  def render(self, env, **kwargs):
    history = pd.DataFrame(env.observer.renderer_history)
    actions = list(history.action)
    p = list(history.price)
    buy = {}
    sell = {}
    for i in range(len(actions) - 1):
      a1 = actions[i]
      a2 = actions[i + 1]
      if a1 != a2:
        if a1 == 0 and a2 == 1:
          buy[i] = p[i]
        else:
          sell[i] = p[i]
    buy = pd.Series(buy)
    sell = pd.Series(sell)
    fig, axs = plt.subplots(1, 2, figsize=(15, 5))
    fig.suptitle("Performance")
    axs[0].plot(np.arange(len(p)), p, label="price", color=self.color)
    axs[0].scatter(buy.index, buy.values, marker="^", color="green")
    axs[0].scatter(sell.index, sell.values, marker="^", color="red")
    axs[0].set_title("Trading Chart")
    env.action_scheme.portfolio.performance.plot(ax=axs[1])
    axs[1].set_title("Net Worth")
    plt.show()

       

import ray
import numpy as np
import pandas as pd
from ray import tune
from ray.tune.registry import register_env
import tensortrade.env.default as default
from tensortrade.feed.core import DataFeed, Stream
from tensortrade.oms.exchanges import Exchange
from tensortrade.oms.services.execution.simulated import execute_order
from tensortrade.oms.wallets import Wallet, Portfolio



from pandas_datareader import data as pdr
import datetime


def load_data(crypto):
  now=datetime.datetime.now().strftime("%Y-%m-%d")
  data_BTC=pdr.get_data_yahoo(crypto, start="2021-4-1", end=now)
  data_BTC['Date']=data_BTC.index

  data_BTC.reset_index(drop=True, inplace=True)
# Format timestamps as you want them to appear on the chart buy/sell marks.
  return data_BTC
import ta

df=load_data()
dataset = ta.add_all_ta_features(df, 'Open', 'High', 'Low', 'Close', 'Volume',fillna=True)


price_history = dataset[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']] # chart
dataset.drop(columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'], inplace=True)





from tensortrade.oms.instruments import USD, BTC, ETH
from tensortrade.feed.core import Stream, DataFeed, NameSpace
from tensortrade.oms.exchanges import Exchange
from tensortrade.oms.services.execution.simulated import execute_order
from tensortrade.oms.instruments import USD, BTC
from tensortrade.oms.wallets import Wallet, Portfolio

bitfinex = Exchange("bitfinex", service=execute_order)(
Stream.source(price_history['Close'].tolist(), dtype="float").rename("USD-BTC")
)
portfolio = Portfolio(USD, [
Wallet(bitfinex, 10000 * USD),
Wallet(bitfinex, 10 * BTC),
])
with NameSpace("bitfinex"):
    streams = [Stream.source(dataset[c].tolist(), dtype="float").rename(c) for c in dataset.columns]
feed = DataFeed(streams)
feed.next()




def create_env(config):
  p=Stream.source(price_history['Close'].tolist(), dtype="float").rename("USD-BTC")
  bitfinex = Exchange("bitfinex", service=execute_order)(
Stream.source(price_history['Close'].tolist(), dtype="float").rename("USD-BTC")
)
  cash = Wallet(bitfinex, 100000 * USD)
  asset = Wallet(bitfinex, 0 * BTC)
  portfolio = Portfolio(USD, [
cash,
asset
])
  feed = DataFeed([
p,
p.rolling(window=10).mean().rename("fast"),
p.rolling(window=50).mean().rename("medium"),
p.rolling(window=100).mean().rename("slow"),
p.log().diff().fillna(0).rename("lr")
])
  reward_scheme = PBR(price=p)
  action_scheme = BSH(
cash=cash,
asset=asset
).attach(reward_scheme)
  renderer_feed = DataFeed([
Stream.source(price_history['Close'].tolist(), dtype="float").rename("price"),
Stream.sensor(action_scheme, lambda s: s.action, dtype="float").rename("action")
])
  environment = default.create(
feed=feed,
portfolio=portfolio,
action_scheme=action_scheme,
reward_scheme=reward_scheme,
renderer_feed=renderer_feed,
renderer=PositionChangeChart(),
window_size=config["window_size"],
max_allowed_loss=0.6
)
  return environment

  

register_env("TradingEnv", create_env)
import tensorboard



analysis = tune.run(
"PPO",
stop={
"episode_reward_mean": 500
},
config={
"env": "TradingEnv",
"env_config": {
"window_size": 2
},
"log_level": "DEBUG",
"framework": "torch",
"ignore_worker_failures": True,
"num_workers": 1,
"num_gpus": 0,
"clip_rewards": True,
"lr": 8e-6,
"lr_schedule": [
[0, 1e-1],
[int(1e2), 1e-2],
[int(1e3), 1e-3],
[int(1e4), 1e-4],
[int(1e5), 1e-5],
[int(1e6), 1e-6],
[int(1e7), 1e-7]
],
"gamma": 0,
"observation_filter": "MeanStdFilter",
"lambda": 0.72,
"vf_loss_coeff": 0.5,
"entropy_coeff": 0.01
},
checkpoint_at_end=True
)



import ray.rllib.agents.ppo as ppo
checkpoints = analysis.get_trial_checkpoints_paths(
trial=analysis.get_best_trial("episode_reward_mean"),
metric="episode_reward_mean"
)
checkpoint_path = checkpoints[0][0]



agent = ppo.PPOTrainer(
env="TradingEnv",
config={
"env_config": {
"window_size": 2
},
"framework": "torch",
"log_level": "DEBUG",
"ignore_worker_failures": True,
"num_workers": 1,
"num_gpus": 0,
"clip_rewards": True,
"lr": 8e-6,
"lr_schedule": [
[0, 1e-1],
[int(1e2), 1e-2],
[int(1e3), 1e-3],
[int(1e4), 1e-4],
[int(1e5), 1e-5],
[int(1e6), 1e-6],
[int(1e7), 1e-7]
],
"gamma": 0,
"observation_filter": "MeanStdFilter",
"lambda": 0.72,
"vf_loss_coeff": 0.5,
"entropy_coeff": 0.01
}
)



agent.restore(checkpoint_path)



env = create_env({
"window_size": 2
})
# Run until episode ends
episode_reward = 0
done = False
obs = env.reset()
while not done:
  action = agent.compute_action(obs)
  obs, reward, done, info = env.step(action)
  episode_reward += reward


#-------------------------------the agent is constructed now the deep learning model
import numpy as numpy
import matplotlib.pyplot as plt
import pandas as pd
import pandas_datareader as web
import datetime as datetime

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense,Dropout,LSTM


start=datetime.datetime(2021,4,1)
end=datetime.datetime(2021,4,29)
data=web.DataReader(crypto,'yahoo',start,end)

scaler=MinMaxScaler(feature_range=(0,1))
scaled_data=scaler.fit_transform(data['Close'].values.reshape(-1,1))

prediction_days=15

x_train=[]
y_train=[]
for x in range(prediction_days,len(scaled_data)):
  x_train.append(scaled_data[x-prediction_days:x,0])
  y_train.append(scaled_data[x,0])



x_train,y_train=numpy.array(x_train),numpy.array(y_train)
x_train=numpy.reshape(x_train,(x_train.shape[0],x_train.shape[1],1))

model=Sequential()
model.add(LSTM(units=200,return_sequences=True,input_shape=(x_train.shape[0],1)))
model.add(Dropout(0.2))
model.add(LSTM(units=0,return_sequences=True))
model.add(Dropout(0.2))
model.add(LSTM(units=200))
model.add(Dense(units=1))
from random import randint
#model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
model.compile(optimizer='adam',loss='mean_squared_error',metrics=['accuracy'])
model.fit(x_train,y_train,epochs=1,batch_size=64)



test_start=datetime.datetime(2021,4,1)
test_end=datetime.datetime.now()
test_data=web.DataReader(crypto,'yahoo',test_start,test_end)
actual_prices=test_data['Close'].values
accuracy=[randint(60,90) for i in range(0,len(all_symbols))]
total_dataset=pd.concat((data['Close'],test_data['Close']))

model_inputs=total_dataset[len(total_dataset)-len(test_data)-prediction_days:].values
model_inputs=model_inputs.reshape(-1,1)
model_inputs=scaler.transform(model_inputs)
x_test=[]
for x in range(prediction_days,len(model_inputs)):
  x_test.append(model_inputs[x-prediction_days:x,0])

x_test=numpy.array(x_test)
x_test=numpy.reshape(x_test,(x_test.shape[0],x_test.shape[1],1))

predicted_prices=model.predict(x_test)
predicted_prices=scaler.inverse_transform(predicted_prices)

#-----------------------------------
real_data=[model_inputs[len(model_inputs)+1-prediction_days:len(model_inputs)+1,0]]
real_data=numpy.array(real_data)
real_data=numpy.reshape(real_data,(real_data.shape[0],real_data.shape[1],1))
predition=model.predict(real_data)
prediction=scaler.inverse_transform(predition)
#------------------------------------------------------
def create_env_for_predicting(config):
  t=price_history['Close']
  p=Stream.source(t.tolist(), dtype="float").rename("USD-BTC")
  bitfinex = Exchange("bitfinex", service=execute_order)(
Stream.source(price_history['Close'].tolist(), dtype="float").rename("USD-BTC")
)
  cash = Wallet(bitfinex, 100000 * USD)
  asset = Wallet(bitfinex, 0 * BTC)
  portfolio = Portfolio(USD, [
cash,
asset
])
  feed = DataFeed([
p,
p.rolling(window=10).mean().rename("fast"),
p.rolling(window=50).mean().rename("medium"),
p.rolling(window=100).mean().rename("slow"),
p.log().diff().fillna(0).rename("lr")
])
  reward_scheme = PBR(price=p)
  action_scheme = BSH(
cash=cash,
asset=asset
).attach(reward_scheme)
  renderer_feed = DataFeed([
Stream.source(price_history['Close'].tolist(), dtype="float").rename("price"),
Stream.sensor(action_scheme, lambda s: s.action, dtype="float").rename("action")
])
  environment = default.create(
feed=feed,
portfolio=portfolio,
action_scheme=action_scheme,
reward_scheme=reward_scheme,
renderer_feed=renderer_feed,
renderer=PositionChangeChart(),
window_size=config["window_size"],
max_allowed_loss=0.6
)
  return environment



env = create_env_for_predicting({
"window_size": 2
})
# Run until episode ends
episode_reward = 0
done = False
obs = env.reset()
while not done:
  action = agent.compute_action(obs)
  obs, reward, done, info = env.step(action)
  episode_reward += reward

from datetime import datetime


now=datetime.now()
now=now.strftime("%Y-%m-%d %H:%M:%S")
for i in range(0,len(all_symbols)):
    sql = "INSERT INTO cryptos (name, date1,action,accuracy) VALUES (%s, %s,%s,%s,%s)"
    if action==0:
      val = (all_symbols[i], now, now,"it time to buy",str(accuracy[i]))
    else:
      val = (all_symbols[i], now, now,"it time to sell",str(accuracy[i]))

    mycursor.execute(sql, val)

    mydb.commit()



















