'''
Copyright 2019 Xilinx Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

'''Modified by Beetlebox Limited for usage with the MNIST Sign Language Database

Modifications published under Apache License 2.0'''

'''
 Copyright 2020 Beetlebox Limited

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
'''

'''Train keras model and convert to TF

Input: The location of the datasets  
Output: The trained neural network model converted to TF format
Parameters: 
        dataset: The directory where the dataset is held
        train: Train the neural network as well as convert to TF format
        no-train: Only convert to TF format
        num_test: The number of test images to be used'''

import csv, argparse
import sys
import os
import argparse
import cv2
import numpy as np
import tensorflow as tf

from tensorflow_model_optimization.quantization.keras import vitis_quantize
from tensorflow import keras
from tensorflow.keras import datasets, utils, layers, models, optimizers
from nn_model import neural_network
from extract_data import extract_data

def train_nn(dataset_loc, train_bool, num_test):
    '''Train keras model and convert to TF
    Input: The location of the datasets  
    Output: The trained neural network model converted to TF format
    Parameters: 
    dataset_loc: The directory where the dataset is held
    train_bool: If true train network, if false do not
    num_test: The number of test images to be used'''
    if (train_bool):
        #Set Parameters
        DATASET_SIZE=27455
        BATCHSIZE=32
        EPOCHS=3
        LEARN_RATE=0.0001
        DECAY_RATE=1e-6
        NUM_IMAGES=10
        #Pre-processes data and trains the neural network

        #Get the column names form the first row of the csv file
        training_dataset_filepath='%ssign_mnist_train/sign_mnist_train.csv' % dataset_loc
        testing_dataset_filepath='%ssign_mnist_test/sign_mnist_test.csv' % dataset_loc

        train_data, train_label, val_data, val_label, testing_data, testing_label=extract_data(training_dataset_filepath, testing_dataset_filepath, num_test)


        model=neural_network()

        model.compile(loss='categorical_crossentropy', 
                optimizer=optimizers.Adam(lr=LEARN_RATE, decay=DECAY_RATE),
                metrics=['accuracy']
                )

        model.fit(train_data,
            train_label,
            batch_size=BATCHSIZE,
            shuffle=True,
            epochs=EPOCHS,
            validation_data=(val_data, val_label)
            )

        #Evaluate Model Accracy
        scores = model.evaluate(testing_data, 
                            testing_label,
                            batch_size=BATCHSIZE
                            )
    
        print('Loss: %.3f' % scores[0])
        print('Accuracy: %.3f' % scores[1])

        # save weights, model architecture & optimizer to an HDF5 format file
        tf.keras.backend.set_learning_phase(0)
        model.save(os.path.join('./train','keras_trained_model.h5'))
        print ('######## Finished Training ########')

    print('######## Loading Float Model ########')
    float_model = tf.keras.models.load_model('./train/keras_trained_model.h5')
    print('######## Quantizing Float Model ########')
    quantizer = vitis_quantize.VitisQuantizer(float_model)
    quantized_model = quantizer.quantize_model(calib_dataset=(val_data, val_label))
    quantized_model.save('./train/quantized_model.h5')
    print('######## Evaluating the Quantized Model ########')
    with vitis_quantize.quantize_scope():
        test_quantized_model = tf.keras.models.load_model('./train/quantized_model.h5')
    test_quantized_model.compile( loss='categorical_crossentropy', 
        metrics= ['accuracy'])
    test_quantized_model.evaluate(testing_data, 
                            testing_label,
                            batch_size=BATCHSIZE)

    #vitis_quantize.VitisQuantizer.dump_model(quantized_model, (testing_data, testing_label), './dump')




def main():
    #The main file for everything that is to be run on host

    #Setup the 
    argpar = argparse.ArgumentParser()

    argpar.add_argument('--dataset',
                    type=str,
                    default='./',
                    help='The directory where the dataset is held')


    argpar.add_argument('--train', dest='train', action='store_true')
    argpar.add_argument('--no-train', dest='train', action='store_false')
    argpar.add_argument('--num_test', dest='num_test', action='store', type=int,)
    argpar.set_defaults(train=True)
    argpar.set_defaults(num_test=10)

    args = argpar.parse_args()  

    train_nn(args.dataset, args.train, args.num_test)

    

if __name__ ==  "__main__":
    main()