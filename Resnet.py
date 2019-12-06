# -*- coding: utf-8 -*-
"""
Created on Fri Sep 13 13:33:34 2019

@author: span21
"""

import tensorflow as tf
import numpy as np
import scipy.io
import matplotlib.pyplot as plt
import os
import cv2
from matplotlib.pyplot import figure
import time

check_pt_path_str = 'checkpoints/'
output_folder = './image/val_256_denoise_Gaussian_3'
batch_size = 16
eval_size = 16
img_height = 256
img_width = 256
img_depth = 3
epochs = 200


def conv_layer(name, layer_input, w):
    return tf.nn.conv2d(layer_input, w, strides=[1, 1, 1, 1], padding='SAME', name=name)

def relu_layer(name, layer_input, b):
    return tf.nn.relu(layer_input + b, name=name)

def pool_layer(name, layer_input):
        return tf.nn.avg_pool2d(layer_input, ksize=[1, 2, 1, 1], strides=[1, 2, 2, 1], padding='SAME', name=name)

def get_weights(name, vgg_layers, i):
    weights = vgg_layers[i][0][0][2][0][0]
    w = tf.Variable(weights, name=name)
    return w

def get_bias(name, vgg_layers, i):
    bias = vgg_layers[i][0][0][2][0][1]
    b = tf.Variable(np.reshape(bias, bias.size), name=name)
    return b

def load_imgs(img_path,label_path):
    img_string = tf.io.read_file(img_path)
    img = tf.image.decode_image(img_string, 3)
    img = tf.compat.v1.image.resize_image_with_pad(img, img_height, img_width,img_depth)
#    _,_,imgdepth = img.shape
#    if imgdepth == 1:
#        img = tf.image.grayscale_to_rgb(img)
    # img = tf.image.adjust_contrast(img,10)
#    img = tf.image.per_image_standardization(img)
    
    label_string = tf.io.read_file(label_path)
    label = tf.image.decode_image(label_string, 3)
    label = tf.compat.v1.image.resize_image_with_pad(label, img_height, img_width,img_depth)
#    _,_,labeldepth = label.shape
#    if labeldepth == 1:
#        label = tf.image.grayscale_to_rgb(label)
    # img = tf.image.adjust_contrast(img,10)
#    label = tf.image.per_image_standardization(label)
    return img,label


def get_train_iterator():
    img_files = np.load('train_imgs.npy')
    img_files = np.sort(img_files)
    labels = np.load('train_lbs.npy')
    labels = np.sort(labels)
    dataset = tf.data.Dataset.from_tensor_slices((img_files, labels))
    dataset = dataset.shuffle(10000)
    dataset = dataset.map(map_func=load_imgs)
#    dataset = dataset.repeat(epochs)
    dataset = dataset.batch(batch_size, drop_remainder=True)
    iterator = dataset.make_initializable_iterator()
    length = len(img_files)
    return iterator,length


def get_eval_iterator():
    img_files = np.load('eval_imgs.npy')
    img_files = np.sort(img_files)
    labels = np.load('eval_lbs.npy')
    labels = np.sort(labels)
    dataset = tf.data.Dataset.from_tensor_slices((img_files, labels))
    dataset = dataset.map(map_func=load_imgs)
    dataset = dataset.batch(batch_size, drop_remainder=True)
    iterator = dataset.make_initializable_iterator()
    length = len(img_files)
    return iterator,length

def get_vali_iterator():
    img_files = np.load('valid_imgs.npy')
    img_files = np.sort(img_files)
    labels = np.load('valid_lbs.npy')
    labels = np.sort(labels)
    dataset = tf.data.Dataset.from_tensor_slices((img_files, labels))
    dataset = dataset.map(map_func=load_imgs)
    dataset = dataset.batch(batch_size, drop_remainder=True)
    iterator = dataset.make_initializable_iterator()
    length = len(img_files)
    return iterator,length

net = {}


def cnn_model_fn():
    print('\nBUILDING VGG-19 NETWORK')

#    print('loading model weights...')
#    vgg_raw_net = scipy.io.loadmat('imagenet-vgg-verydeep-19.mat')
#    vgg_layers = vgg_raw_net['layers'][0]
    print('constructing layers...')

    net['input'] = tf.compat.v1.placeholder(tf.float32, shape=[batch_size, img_height, img_width, img_depth])
    net['labels'] = tf.compat.v1.placeholder(tf.float32, shape=[batch_size, img_height, img_width, img_depth])

    print('Pre_block 1')
    net['conv1_0'] = tf.layers.conv2d(net['input'], filters = 64, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
    #    net['bn1_1'] = tf.layers.batch_normalization(net['conv1_1'], training=False, momentum=0.9)
    
    print('Convolution_block 1')
    net['conv1_1'] = tf.layers.conv2d(net['conv1_0'], filters = 64, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
    net['bnc1_1'] = tf.layers.batch_normalization(net['conv1_1'], training=True, momentum=0.9)
    net['conv1_2'] = tf.layers.conv2d(net['bnc1_1'], filters = 64, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
#    net['bnc1_2'] = tf.layers.batch_normalization(net['conv1_2'], training=True, momentum=0.9)
#    net['conv1_3'] = tf.layers.conv2d(net['bnc1_2'], filters = 128, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
    net['bnc1_3'] = tf.layers.batch_normalization(net['conv1_2'], training=True, momentum=0.9)
    net['short_cut1_1'] = tf.layers.conv2d(net['bnc1_3'], filters = 64, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
    
    net['conv_output_1'] = tf.math.add(net['bnc1_3'],net['short_cut1_1'])
    net['conv_output_2'] = tf.compat.v1.keras.layers.ReLU()(net['conv_output_1'])
    
    
    print('Res_block 1')
    net['res1_1'] = tf.layers.conv2d(net['conv_output_2'], filters = 64, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
    net['bnr1_1'] = tf.layers.batch_normalization(net['res1_1'], training=True, momentum=0.9)
    net['res1_2'] = tf.layers.conv2d(net['bnr1_1'], filters = 64, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
    net['bnr1_2'] = tf.layers.batch_normalization(net['res1_2'], training=True, momentum=0.9)
#    net['res1_3'] = tf.layers.conv2d(net['bnr1_2'], filters = 128, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
#    net['bnr1_3'] = tf.layers.batch_normalization(net['res1_3'], training=True, momentum=0.9)
    
    net['res_output_1_1'] = tf.math.add(net['bnr1_2'],net['conv_output_2'])
    net['res_output_1_2'] = tf.compat.v1.keras.layers.ReLU()(net['res_output_1_1'])
    
#    print('Res_block 2')
#    net['res2_1'] = tf.layers.conv2d(net['res_output_1_2'], filters = 64, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
#    net['bnr2_1'] = tf.layers.batch_normalization(net['res1_1'], training=True, momentum=0.9)
#    net['res2_2'] = tf.layers.conv2d(net['bnr1_1'], filters = 64, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
#    net['bnr2_2'] = tf.layers.batch_normalization(net['res1_2'], training=True, momentum=0.9)
#    net['res2_3'] = tf.layers.conv2d(net['bnr1_2'], filters = 128, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())
#    net['bnr2_3'] = tf.layers.batch_normalization(net['res1_3'], training=True, momentum=0.9)
    
#    net['res_output_2_1'] = tf.math.add(net['bnr2_3'],net['res_output_1_2'])
#    net['res_output_2_2'] = tf.compat.v1.keras.layers.ReLU()(net['res_output_2_1'])

    output = tf.layers.conv2d(net['res_output_1_2'], filters = 3, kernel_size = [3,3],padding = 'SAME', activation=tf.nn.relu,use_bias=True,bias_initializer=tf.zeros_initializer())

    original_loss = tf.compat.v1.losses.mean_squared_error(labels=net['input'],\
                                                  predictions=net['labels'])
    loss = tf.compat.v1.losses.mean_squared_error(labels=net['labels'],\
                                                  predictions=output)
    return loss,net['labels'],original_loss,output



def main(Command):
    tf.logging.set_verbosity(tf.logging.INFO)

    loss, labels,original_loss,output = cnn_model_fn()

    optimizer = tf.compat.v1.train.AdamOptimizer(learning_rate=0.001, epsilon=1e-8, use_locking=False)

    train_op = optimizer.minimize(loss)

    # Get the iterator for the data set
    itr_train,train_len = get_train_iterator()
    next_train_batch = itr_train.get_next()

    itr_eval,eval_len = get_eval_iterator()
    next_eval_batch = itr_eval.get_next()
    
    itr_vali,vali_len = get_vali_iterator()
    next_vali_batch = itr_vali.get_next()
    elapsed = []
    # Define the saver for storing variables
    saver = tf.compat.v1.train.Saver(tf.compat.v1.trainable_variables(), max_to_keep=0)

    # The counter for tracking the number of batches
    
    with tf.device('/gpu:0'), tf.Session() as sess:
        sess.run(tf.compat.v1.global_variables_initializer())
        sess.run(tf.compat.v1.local_variables_initializer())

        latest_checkpoint = tf.compat.v1.train.latest_checkpoint(check_pt_path_str)
        if latest_checkpoint is not None:
            saver.restore(sess, latest_checkpoint)
            # saver.restore(sess, 'checkpoints/epoch_30_model.ckpt')

        if Command == "train":            
            train_loss_list = []
            eval_loss_list = []
            for idx_epoch in range(epochs):
                t = time.time()
                # Reset the iterator
                sess.run(itr_train.initializer)
                sess.run(itr_eval.initializer)
                # Var for loss calculation
                batch_count = 0
                batch_loss = 0
                avg_loss = 0
                print("Start Training for epoch:",idx_epoch,"...")
                for i in range(1,int(train_len/batch_size)+1):
                    train_data, train_label = sess.run(next_train_batch)
                    _, _, _, channel = train_data.shape
                    if channel == 3:
                        train_dict = {net['input']: train_data, net['labels']: train_label}
                        # Train the model
                        update_ops = tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.UPDATE_OPS)
                        with tf.control_dependencies(update_ops):
                            sess.run(train_op, feed_dict=train_dict)
                            loss_val = sess.run(loss, feed_dict=train_dict)
                            print('loss: '+  str(loss_val))           
                            original_loss_val = sess.run(original_loss,feed_dict=train_dict)   
                            print('original_loss: '+  str(original_loss_val))                                   
                        batch_count += 1
                        batch_loss += loss_val
                        avg_loss = batch_loss/batch_count
                        print('avg_loss: ' + str(avg_loss))
                        print('batch_count: '+ str(batch_count))
                print('Epoch', idx_epoch, ' Avg_loss:', avg_loss)
                train_loss_list.append(avg_loss)
                if idx_epoch % 10 == 0:
                    print("saving checkpoint every 2 epoches...")
                    saver.save(sess, check_pt_path_str + 'epoch_' + str(idx_epoch) + '_model.ckpt')
                # Calc Eval loss
                batch_count = 0
                batch_loss = 0
                avg_loss = 0
                for i in range(1,int(eval_len/batch_size)+1):
                    try:
                        eval_data, eval_label = sess.run(next_eval_batch)
                        eval_dict = {net['input']: eval_data, net['labels']: eval_label}
                        loss_val = sess.run(loss, feed_dict=eval_dict)
                        batch_loss += loss_val
                        batch_count += 1
                    except:
                        break
                avg_loss = batch_loss / batch_count
                eval_loss_list.append(avg_loss)
                print('Epoch', idx_epoch, 'Eval Loss:', avg_loss)
                
                figure(dpi=100)
                plt.plot(train_loss_list, linewidth=2)
                plt.plot(eval_loss_list, linewidth=2)
                plt.legend(['train_loss_list','eval_loss_list'])
                plt.xlabel('Epoch')
                plt.ylabel('MSE loss')
                plt.title('Performance vs. loss')
                plt.savefig(check_pt_path_str + str(idx_epoch) + '.png', bbox_inches='tight', pad_inches=0)
                elapsed.append(time.time() - t)
                print(str(elapsed[idx_epoch])+'s')
                t = time.time()
                np.save('time_record', elapsed)
        elif Command == "eval":
            print("evaluating...")
            sess.run(itr_train.initializer)
            sess.run(itr_eval.initializer)
            sess.run(itr_vali.initializer)
            ind = 0
            if not os.path.isdir(output_folder):
                os.mkdir(output_folder)
            if not os.path.isdir(output_folder+'/Truth'):
                os.mkdir(output_folder+'/Truth')
            if not os.path.isdir(output_folder+'/Noisy'):
                os.mkdir(output_folder+'/Noisy')
            Creation_num = 2
            for i in range(1,Creation_num):
                vali_data, vali_label = sess.run(next_vali_batch)
                vali_dict = {net['input']: vali_data, net['labels']: vali_label}
                truth = sess.run(labels, feed_dict=vali_dict)
                prediction = sess.run(output, feed_dict=vali_dict)
                Noisy_img = sess.run(net['input'], feed_dict=vali_dict)
                for j in range(batch_size):
                    img = truth[j,:,:,:]
                    RGBimg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    cv2.imwrite(output_folder+'/Truth/'+'/Truth00'+str(ind)+'.jpg', RGBimg)
                    img = prediction[j,:,:,:]
                    RGBimg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    cv2.imwrite(output_folder+'/Pre00'+str(ind)+'.jpg',RGBimg)
                    noisy_img = Noisy_img[j,:,:,:]
                    RGBimg = cv2.cvtColor(noisy_img, cv2.COLOR_BGR2RGB)
                    cv2.imwrite(output_folder+'/Noisy/'+'/Noisy00'+str(ind)+'.jpg',RGBimg)
                    ind += 1
                loss_val = sess.run(loss, feed_dict=vali_dict)
                print('loss: '+  str(loss_val))           
                original_loss_val = sess.run(original_loss,feed_dict=vali_dict)   
                print('original_loss: '+  str(original_loss_val))        
        else:
            print("unrecognized mode!!!")


if __name__ == "__main__":
    main("eval")