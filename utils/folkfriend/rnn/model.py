from tensorflow import keras
from tensorflow.keras import layers

from folkfriend import ff_config


def vgg_style(input_tensor):
    x = layers.Conv2D(8, 3, padding='same', activation='relu')(input_tensor)
    x = layers.MaxPool2D(pool_size=2, padding='same')(x)

    x = layers.Conv2D(16, 3, padding='same', activation='relu')(x)
    x = layers.MaxPool2D(pool_size=2, padding='same')(x)

    x = layers.Conv2D(32, 3, padding='same', use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.Conv2D(32, 3, padding='same', activation='relu')(x)
    x = layers.MaxPool2D(pool_size=2, strides=(2, 1), padding='same')(x)

    x = layers.Conv2D(64, 3, padding='same', use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.Conv2D(64, 3, padding='same', activation='relu')(x)
    x = layers.MaxPool2D(pool_size=2, strides=(2, 1), padding='same')(x)

    x = layers.Conv2D(64, 2, use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    return x


def build_model():
    """build CNN-RNN model"""

    # img_input = keras.Input(shape=(ff_config.MIDI_NUM, image_width, channels))
    inputs = keras.Input(shape=(ff_config.SPEC_NUM_FRAMES, ff_config.MIDI_NUM))
    # x = vgg_style(img_input)
    # x = layers.Reshape((-1, 64))(x)

    x = inputs
    x = layers.Bidirectional(layers.LSTM(units=72, return_sequences=True))(x)
    x = layers.Bidirectional(layers.LSTM(units=72, return_sequences=True))(x)
    # x = layers.Bidirectional(layers.LSTM(units=16, return_sequences=True))(x)
    # x = layers.Bidirectional(layers.LSTM(units=16, return_sequences=True))(x)
    # x = layers.Dropout(0.1)(x)
    # x = layers.Bidirectional(layers.LSTM(units=96, return_sequences=True))(x)
    x = layers.Dense(units=ff_config.RNN_CLASSES_NUM)(x)
    return keras.Model(inputs=inputs, outputs=x, name='CRNN')