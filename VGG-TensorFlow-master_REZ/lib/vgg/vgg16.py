import tensorflow as tf
import numpy as np
from lib.networks.base_network import Net
import math

class VGG16(Net):
    def __init__(self, cfg_):
        super().__init__(cfg_)
        self.x = tf.placeholder(tf.float32, name='x', shape=[self.config.batch_size,
                                                             self.config.image_width,
                                                             self.config.image_height,
                                                             self.config.image_depth], )
        self.y = tf.placeholder(tf.int16, name='y', shape=[self.config.batch_size,
                                                           self.config.n_classes])
        self.loss = None
        self.accuracy = None
        self.summary = []

    def init_saver(self):
        pass

    def get_summary(self):
        return self.summary

    def conv(self, layer_name, bottom, out_channels, kernel_size = 2 , stride=[1, 1, 1,1],inchan=3,d = 0):
     with tf.variable_scope(layer_name):
        
        
        
        
        #    w = tf.get_variable(name='weights',
         #                       trainable=self.config.is_pretrain,
          #                      shape=[kernel_size[0], kernel_size[1],
           #                            inchan, out_channels],
            #                    initializer=tf.contrib.layers.xavier_initializer())
            b = tf.get_variable(name='biases',
                                trainable=self.config.is_pretrain,
                                shape=[out_channels],
                                initializer=tf.constant_initializer(0.0))

     #print('\n\n\n\n\n\n\n',bottom.get_shape()[-1],'\n\n\n\n\n\n' )


     bottom = tf.pad(
               bottom, [[0, 0], [2, 2], [2, 2], [0, 0]], 'CONSTANT')
     if out_channels == 64:
               rez = [4, 4, 4]
     elif out_channels == 128:
               rez = [4, 8, 4]
     elif out_channels == 256:
               rez = [8, 8, 4]
     elif out_channels == 512:
               rez = [8, 8, 8]               
     elif out_channels == 1024:
               rez = [16, 8, 8]               

     W1 = tf.Variable(tf.truncated_normal([kernel_size, rez[0]], stddev=1./math.sqrt(kernel_size)))
     W11 = tf.Variable(tf.truncated_normal([kernel_size, rez[1]], stddev=1./math.sqrt(kernel_size)))
     W111 = tf.Variable(tf.truncated_normal([inchan, rez[2]], stddev=1./math.sqrt(kernel_size)))
     e = tf.extract_image_patches(bottom, [1, 2, 2, 1], [1, 1, 1, 1], [1, 1, 1, 1], 'SAME')
     patches = tf.reshape(e, [-1, kernel_size, kernel_size,d**2,inchan])
     bottom = tf.reshape(tf.tensordot(tf.tensordot(tf.tensordot(patches, W111, [
                     4, 0]), W11, [2, 0]), W1, [1, 0]), [-1, d, d, out_channels])            
#           bottom= tf.nn.conv2d(bottom, w, stride, padding='SAME', name='conv')
     bottom = tf.nn.bias_add(bottom, b, name='bias_add')
     bottom = tf.nn.relu(bottom, name='relu')
     return bottom

    def pool(self, layer_name, bottom, kernel=[1, 2, 2, 1], stride=[1, 2, 2, 1], is_max_pool=True):
        with tf.name_scope(layer_name):
            if is_max_pool:
                bottom = tf.nn.max_pool(bottom, kernel, stride, padding='SAME', name=layer_name)
            else:
                bottom = tf.nn.avg_pool(bottom, kernel, stride, padding='SAME', name=layer_name)
            return bottom

    def fc(self, layer_name, bottom, out_nodes):
        shape = bottom.get_shape()
        if len(shape) == 4:  # x is 4D tensor
            size = shape[1].value * shape[2].value * shape[3].value
        else:  # x has already flattened
            size = shape[-1].value
        with tf.variable_scope(layer_name):
            w = tf.get_variable('weights',
                                shape=[size, out_nodes],
                                initializer=tf.contrib.layers.xavier_initializer())
            b = tf.get_variable('biases',
                                shape=[out_nodes],
                                initializer=tf.constant_initializer(0.0))
            flat_x = tf.reshape(bottom, [-1, size])
            bottom = tf.nn.bias_add(tf.matmul(flat_x, w), b)
            bottom = tf.nn.relu(bottom)
            return bottom

    def bn(self, layer_name, bottom):
        with tf.name_scope(layer_name):
            epsilon = 1e-3
            batch_mean, batch_var = tf.nn.moments(bottom, [0])
            bottom = tf.nn.batch_normalization(bottom, mean=batch_mean, variance=batch_var, offset=None,
                                               scale=None, variance_epsilon=epsilon)
            return bottom

    def batch_normalization(self, layer_name, bottom, training=True):
        with tf.name_scope(layer_name):
            epsilon = 1e-3
            bottom = tf.layers.batch_normalization(bottom, epsilon=epsilon, training=training)
            return bottom

    def cal_loss(self, logits, labels):
        with tf.name_scope('loss') as scope:
            cross_entropy = tf.nn.softmax_cross_entropy_with_logits(
                logits=logits, labels=labels, name='cross-entropy')
            self.loss = tf.reduce_mean(cross_entropy, name='loss')
            loss_summary = tf.summary.scalar(scope, self.loss)
            self.summary.append(loss_summary)

    def cal_accuracy(self, logits, labels):
        with tf.name_scope('accuracy') as scope:
            correct = tf.equal(tf.argmax(logits, 1), tf.argmax(labels, 1))
            correct = tf.cast(correct, tf.float32)
            self.accuracy = tf.reduce_mean(correct) * 100.0
            accuracy_summary = tf.summary.scalar(scope, self.accuracy)
            self.summary.append(accuracy_summary)

    # def num_correct_prediction(self, logits, labels):
    #     correct = tf.equal(tf.arg_max(logits, 1), tf.arg_max(labels, 1))
    #     correct = tf.cast(correct, tf.int32)
    #     n_correct = tf.reduce_sum(correct)
    #     return n_correct

    def optimize(self):
        with tf.name_scope('optimizer'):
            optimizer = tf.train.GradientDescentOptimizer(learning_rate=self.config.learning_rate)
            # optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
            train_op = optimizer.minimize(self.loss, global_step=self.global_step_tensor)
            return train_op

    def build_model(self):

        self.conv1_1 = self.conv('conv1_1', self.x, 64, stride=[1, 1, 1, 1],inchan=3,d = 32)#30
        self.conv1_2 = self.conv('conv1_2', self.conv1_1, 64, stride=[1, 1, 1, 1],inchan=64,d = 32)#30
        self.conv1_3 = self.conv('conv1_3', self.conv1_2, 64, stride=[1, 1, 1, 1],inchan=64,d = 32)#30
        self.conv1_4 = self.conv('conv1_4', self.conv1_3, 64, stride=[1, 1, 1, 1],inchan=64,d = 32)#30
        self.conv1_5 = self.conv('conv1_5', self.conv1_4, 64, stride=[1, 1, 1, 1],inchan=64,d = 32)#30
        self.conv1_6 = self.conv('conv1_6', self.conv1_5, 64, stride=[1, 1, 1, 1],inchan=64,d = 32)#30
        self.conv1_7 = self.conv('conv1_7', self.conv1_6, 64, stride=[1, 1, 1, 1],inchan=64,d = 32)#30
        self.pool1 = self.pool('pool1', self.conv1_2, kernel=[1, 2, 2, 1], stride=[1, 2, 2, 1], is_max_pool=True)

        self.conv2_1 = self.conv('conv2_1', self.pool1, 128, stride=[1, 1, 1, 1],inchan=64,d = 16)#16
        self.conv2_2 = self.conv('conv2_2', self.conv2_1, 128, stride=[1, 1, 1, 1],inchan=128,d = 16)#16
        self.conv2_3 = self.conv('conv2_3', self.conv2_2, 128, stride=[1, 1, 1, 1],inchan=128,d = 16)#16
        self.conv2_4 = self.conv('conv2_4', self.conv2_3, 128, stride=[1, 1, 1, 1],inchan=128,d = 16)#16
        self.conv2_5 = self.conv('conv2_5', self.conv2_4, 128, stride=[1, 1, 1, 1],inchan=128,d = 16)#16
        self.pool2 = self.pool('pool2', self.conv2_2, kernel=[1, 2, 2, 1], stride=[1, 2, 2, 1], is_max_pool=True)

        self.conv3_1 = self.conv('conv3_1', self.pool2, 256, stride=[1, 1, 1, 1],inchan=128,d = 8)#8
        self.conv3_2 = self.conv('conv3_2', self.conv3_1, 256, stride=[1, 1, 1, 1],inchan=256,d = 8)#8
        self.conv3_3 = self.conv('conv3_3', self.conv3_2, 256, stride=[1, 1, 1, 1],inchan=256,d = 8)#8
        self.conv3_4 = self.conv('conv3_4', self.conv3_3, 256, stride=[1, 1, 1, 1],inchan=256,d = 8)#8
        self.conv3_5 = self.conv('conv3_5', self.conv3_4, 256, stride=[1, 1, 1, 1],inchan=256,d = 8)#8
        self.conv3_6 = self.conv('conv3_6', self.conv3_5, 256, stride=[1, 1, 1, 1],inchan=256,d = 8)#8
        self.pool3 = self.pool('pool3', self.conv3_3, kernel=[1, 2, 2, 1], stride=[1, 2, 2, 1], is_max_pool=True)

        self.conv4_1 = self.conv('conv4_1', self.pool3, 512, stride=[1, 1, 1, 1],inchan=256,d = 4)#4
        self.conv4_2 = self.conv('conv4_2', self.conv4_1, 512, stride=[1, 1, 1, 1],inchan=512,d = 4)#4
        self.conv4_3 = self.conv('conv4_3', self.conv4_2, 512, stride=[1, 1, 1, 1],inchan=512,d = 4)#4
        self.conv4_4 = self.conv('conv4_4', self.conv4_3, 512, stride=[1, 1, 1, 1],inchan=512,d = 4)#4
        self.conv4_5 = self.conv('conv4_5', self.conv4_4, 512, stride=[1, 1, 1, 1],inchan=512,d = 4)#4
        self.conv4_6 = self.conv('conv4_6', self.conv4_5, 512, stride=[1, 1, 1, 1],inchan=512,d = 4)#4
        self.pool4 = self.pool('pool4', self.conv4_3, kernel=[1, 2, 2, 1], stride=[1, 2, 2, 1], is_max_pool=True)

        self.conv5_1 = self.conv('conv5_1', self.pool4, 512, stride=[1, 1, 1, 1],inchan=512,d = 2)#2
        self.conv5_2 = self.conv('conv5_2', self.conv5_1, 512, stride=[1, 1, 1, 1],inchan=512,d = 2)#2
        self.conv5_3 = self.conv('conv5_3', self.conv5_2, 512, stride=[1, 1, 1, 1],inchan=512,d = 2)#2
        self.conv5_4 = self.conv('conv5_4', self.conv5_3, 512, stride=[1, 1, 1, 1],inchan=512,d = 2)#2
        self.conv5_5 = self.conv('conv5_5', self.conv5_4, 512, stride=[1, 1, 1, 1],inchan=512,d = 2)#2
        self.conv5_6 = self.conv('conv5_6', self.conv5_5, 512, stride=[1, 1, 1, 1],inchan=512,d = 2)#2
        self.pool5 = self.pool('pool5', self.conv5_3, kernel=[1, 2, 2, 1], stride=[1, 2, 2, 1], is_max_pool=True)




        self.conv6_1 = self.conv('conv6_1', self.pool5, 1024, stride=[1, 1, 1, 1],inchan=512,d = 2)#2
        self.conv6_2 = self.conv('conv6_2', self.conv6_1, 1024, stride=[1, 1, 1, 1],inchan=1024,d = 2)#2
        self.conv6_3 = self.conv('conv6_3', self.conv6_2, 1024, stride=[1, 1, 1, 1],inchan=1024,d = 2)#2
        self.conv6_4 = self.conv('conv6_4', self.conv6_3, 1024, stride=[1, 1, 1, 1],inchan=1024,d = 2)#2
        self.conv6_5 = self.conv('conv6_5', self.conv6_4, 1024, stride=[1, 1, 1, 1],inchan=1024,d = 2)#2
        self.conv6_6 = self.conv('conv6_6', self.conv6_5, 1024, stride=[1, 1, 1, 1],inchan=1024,d = 2)#2
        self.pool6 = self.pool('pool6', self.conv6_3, kernel=[1, 2, 2, 1], stride=[1, 2, 2, 1], is_max_pool=True)
        
        
        
        self.fc6 = self.fc('fc6', self.pool5, out_nodes=8192)
        self.batch_norm1 = self.batch_normalization('batch_norm1', self.fc6, training=self.is_training)
        self.fc7 = self.fc('fc7', self.batch_norm1, out_nodes=8192)
        self.batch_norm2 = self.batch_normalization('batch_norm2', self.fc7, training=self.is_training)
        self.logits = self.fc('fc8', self.batch_norm2, out_nodes=self.config.n_classes)

        self.cal_loss(self.logits, self.y)
        self.cal_accuracy(self.logits, self.y)
        train_op = self.optimize()
        return train_op

    def load_with_skip(self, data_path, session, skip_layer):
        data_dict = np.load(data_path, encoding='latin1').item()  # type: dict
        for key in data_dict.keys():
            if key not in skip_layer:
                with tf.variable_scope(key, reuse=True, auxiliary_name_scope=False):
                # with tf.variable_scope(key, reuse=True):
                    for subkey, data in zip(('weights', 'biases'), data_dict[key]):
                        session.run(tf.get_variable(subkey).assign(data))
