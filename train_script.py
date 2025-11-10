# train_script.py - Script para Treinamento e Geração do Modelo .h5

import tensorflow as tf
from tensorflow import keras
from keras import layers
import numpy as np

# ==============================================================================
# ARQUITETURA U-NET
# ==============================================================================

def conv_block(input_tensor, num_filters):
    """Bloco de Duas Convoluções Seguidas com Ativação ReLU."""
    x = layers.Conv2D(num_filters, (3, 3), padding='same', kernel_initializer='he_normal')(input_tensor)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    
    x = layers.Conv2D(num_filters, (3, 3), padding='same', kernel_initializer='he_normal')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    
    return x

def create_unet_model(input_size=(256, 256, 3), num_classes=1):
    """Cria a arquitetura U-Net."""
    inputs = layers.Input(input_size)
    
    # ENCODER
    c1 = conv_block(inputs, 16); p1 = layers.MaxPooling2D((2, 2))(c1)
    c2 = conv_block(p1, 32); p2 = layers.MaxPooling2D((2, 2))(c2)
    c3 = conv_block(p2, 64); p3 = layers.MaxPooling2D((2, 2))(c3)
    c4 = conv_block(p3, 128); p4 = layers.MaxPooling2D((2, 2))(c4)
    
    # BOTTOM
    c5 = conv_block(p4, 256)

    # DECODER
    u6 = layers.Conv2DTranspose(128, (2, 2), strides=(2, 2), padding='same')(c5); u6 = layers.concatenate([u6, c4])
    c6 = conv_block(u6, 128)
    u7 = layers.Conv2DTranspose(64, (2, 2), strides=(2, 2), padding='same')(c6); u7 = layers.concatenate([u7, c3])
    c7 = conv_block(u7, 64)
    u8 = layers.Conv2DTranspose(32, (2, 2), strides=(2, 2), padding='same')(c7); u8 = layers.concatenate([u8, c2])
    c8 = conv_block(u8, 32)
    u9 = layers.Conv2DTranspose(16, (2, 2), strides=(2, 2), padding='same')(c8); u9 = layers.concatenate([u9, c1], axis=3)
    c9 = conv_block(u9, 16)

    # SAÍDA (1 canal para segmentação binária)
    outputs = layers.Conv2D(num_classes, (1, 1), activation='sigmoid')(c9)
    
    model = keras.Model(inputs=[inputs], outputs=[outputs])
    return model

# ==============================================================================
# FUNÇÃO DE LOSS (Dice Loss - Comum em Imagens Médicas)
# ==============================================================================

def dice_loss(y_true, y_pred, smooth=1e-6):
    y_true_f = keras.backend.flatten(y_true)
    y_pred_f = keras.backend.flatten(y_pred)
    intersection = keras.backend.sum(y_true_f * y_pred_f)
    score = (2. * intersection + smooth) / (keras.backend.sum(y_true_f) + keras.backend.sum(y_pred_f) + smooth)
    return 1.0 - score

# ==============================================================================
# EXECUÇÃO E SALVAMENTO DO MODELO
# ==============================================================================

if __name__ == '__main__':
    
    # ⚠️ 1. Substitua isso pelo carregamento dos seus dados de treinamento reais (Imagens e Máscaras)
    INPUT_H, INPUT_W = 256, 256
    N_SAMPLES = 30 
    
    print("Criando dados de treinamento SIMULADOS (Substitua pelos seus dados reais!)")
    X_train = np.random.rand(N_SAMPLES, INPUT_H, INPUT_W, 3).astype(np.float32) 
    Y_train = np.random.randint(0, 2, (N_SAMPLES, INPUT_H, INPUT_W, 1)).astype(np.float32) 

    # 2. Construção e Compilação
    unet_model = create_unet_model(input_size=(INPUT_H, INPUT_W, 3), num_classes=1)
    
    unet_model.compile(optimizer='adam', 
                       loss=dice_loss, 
                       metrics=['accuracy', tf.keras.metrics.MeanIoU(num_classes=2)]) 

    # 3. Treinamento
    print("Iniciando treinamento...")
    # ATENÇÃO: Use um número de épocas maior (ex: 50-100) e seus dados reais para um resultado significativo
    unet_model.fit(X_train, Y_train, 
                   epochs=5, 
                   batch_size=16, 
                   validation_split=0.1, 
                   verbose=1)

    # 4. Salvamento
    MODEL_FILENAME = 'seu_modelo_segmentacao.h5'
    unet_model.save(MODEL_FILENAME)
    print(f"\n✅ Modelo salvo com sucesso: {MODEL_FILENAME}. Use este arquivo no seu webstream-linux.py")