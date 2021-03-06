# -*- coding: utf-8 -*-
"""CryptoCurrency Prediction RNN

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/121ff-NrhBOepM3EFRx7CJngnobxRyWs9
"""

import pandas as pd
import time
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, LSTM, BatchNormalization
from tensorflow.keras.callbacks import TensorBoard
from tensorflow.keras.callbacks import ModelCheckpoint

"""recurrent neural network to predict against a time-series dataset, cryptocurrency prices."""

prev_time = 60    # how long of a preceeding sequence to collect for RNN in minutes
future_time = 3    # how far into the future are we trying to predict? in minutes
currency_to_predict = 'LTC-USD'

def classify(current, future):
  if float(future > float(current)):
    return 1
  else:
    return 0

main_df = pd.DataFrame()     # Begin Empty

ratios = ['BTC-USD', 'LTC-USD', 'BCH-USD', 'ETH-USD']  # the 4 ratios we want to consider

for ratio in ratios:
  print(ratio)
  dataset = f'/content/drive/MyDrive/Colab Notebooks/DL Basics with python and Keras Sentdex/crypto_data/{ratio}.csv'    # get the full path to the file.
  df = pd.read_csv(dataset, names = ['time', 'low', 'high', 'open', 'close', 'volume'])   # read in specific file

  # rename volume and close to include the ticker so we can still which close/volume is which:
  df.rename(columns = {'close': f'{ratio}_close', 'volume': f'{ratio}_volume'}, inplace = True)

  df.set_index('time', inplace = True)    # set time as index so we can join them on this shared time
  df = df[[f'{ratio}_close', f'{ratio}_volume']]   # ignore the other columns besides price and volume


  if len(main_df) == 0:     # if the dataframe is empty
    main_df = df            # then it's just the current df
  else:                     # otherwisw, join this data to the main one
    main_df = main_df.join(df)

main_df.fillna(method = 'ffill', inplace = True)   # if there are gaps in data, use previously known values
main_df.dropna(inplace = True)   # Drop missing values and update the dataframe itself
print(main_df.head())

main_df['future'] = main_df[f'{currency_to_predict}_close'].shift(-future_time)   # shift up the column by 3 values

main_df.head(15)

main_df[:-1]

main_df['target'] = list(map(classify, main_df[f'{RATIO_TO_PREDICT}_close'], main_df['future']))   # map it to classify function to buy or sell

main_df.head(10)

times = sorted(main_df.index.values)    # get the times
last_5_percent = sorted(main_df.index.values)[-int(0.05 * len(times))]   # get the last 5 % of the times

validation_main_df = main_df[(main_df.index >= last_5_percent)]    # make the validation data where the index is in the last 5%
main_df = main_df[(main_df.index < last_5_percent)]    # now the main_df is all the data up to the last 5%

from sklearn import preprocessing

def preprocess_df(df):
  df = df.drop('future', 1)       # drop the column named 'future', 1 is for column

  for col in df.columns:
    if col != 'target':
      df[col] = df[col].pct_change()    # pct change(percent change from previous value) "normalizes" the different currencies (each crypto coin has vastly diff values, we're really more interested in the other coin's movements)
      df.dropna(inplace = True)    # remove the nas/nans created by pct_change
      df[col] = preprocessing.scale(df[col].values)    # scale between 0 and 1.

  df.dropna(inplace = True)
  sequential_data = []  # this is a list that will contain the sequences
  prev_days = deque(maxlen = prev_time)     # These will be our actual sequences. They are made with deque, which keeps the maximum length by popping out older values as new ones come in

  for i in df.values:
    prev_days.append([n for n in i[:-1]])    # store all but the target
    if len(prev_days) == prev_time:    # make sure we have 60 sequences
      sequential_data.append([np.array(prev_days), i[-1]])

  random.shuffle(sequential_data)    # shuffle for good
  buys = []                   # list that will store our buy sequences and targets
  sells = []     # list that will store our sell sequences and targets

  for seq, target in sequential_data:
    if target == 0:
      sells.append([seq, target])
    elif target == 1:
      buys.append([seq, target])
  
  random.shuffle(buys)
  random.shuffle(sells)

  lower = min(len(buys), len(sells))   # what is the shorter length
  buys = buys[:lower]    # make sure both lists are only up to the shortest length.
  sells = sells[:lower]

  sequential_data = buys + sells
  random.shuffle(sequential_data)   # another shuffle, so the model doesn't get confused with all 1 class then the other.

  X = []
  y = []

  for seq, target in sequential_data:
    X.append(seq)    # X is the sequences
    y.append(target)         # y is the targets/labels (buys vs sell/notbuy)
  
  return np.array(X), y    # return X and y...and make X a numpy array!

train_x, train_y = preprocess_df(main_df)
validation_x, validation_y = preprocess_df(validation_main_df)

print(f"train data: {len(train_x)} validation: {len(validation_x)}")
print(f"Dont buys: {train_y.count(0)}, buys: {train_y.count(1)}")
print(f"VALIDATION Dont buys: {validation_y.count(0)}, buys: {validation_y.count(1)}")

EPOCHS = 10
BATCH_SIZE = 64  #Try smaller batch if you're getting OOM (out of memory) errors.
NAME = f"{prev_time}-SEQ-{future_time}-PRED-{int(time.time())}"  # a unique name for the model

model = Sequential()
model.add(LSTM(128, input_shape=(train_x.shape[1:]), return_sequences = True))
model.add(Dropout(0.2))
model.add(BatchNormalization())  #normalizes activation outputs, same reason you want to normalize your input data.

model.add(LSTM(128, return_sequences = True))
model.add(Dropout(0.1))
model.add(BatchNormalization())

model.add(LSTM(128))
model.add(Dropout(0.2))
model.add(BatchNormalization())

model.add(Dense(32, activation='relu'))
model.add(Dropout(0.2))

model.add(Dense(2, activation='softmax'))

opt = tf.keras.optimizers.Adam(lr=0.001, decay=1e-6)

model.compile(
    loss = 'sparse_categorical_crossentropy',
    optimizer=opt,
    metrics=['accuracy']
)

tensorboard = TensorBoard(log_dir='logs/{}'.format(NAME))

filepath = "RNN_Final-{epoch:02d}-{val_acc:.3f}"  # unique file name that will include the epoch and the validation acc for that epoch
checkpoint = ModelCheckpoint("models/{}.model".format(filepath, monitor='val_acc', verbose=1, save_best_only=True, mode='max')) # saves only the best ones

# Train model
history = model.fit(train_x, train_y,
                    batch_size = BATCH_SIZE,
                    epochs = EPOCHS,
                    validation_data = (validation_x, validation_y),
                    callbacks = [tensorboard, checkpoint])

score = model.evaluate(validation_x, validation_y, verbose = 0)
print('Test Loss: ', score[0])
print('Test accuracy: ', score[1])

model.save("models/{}".format(NAME))

