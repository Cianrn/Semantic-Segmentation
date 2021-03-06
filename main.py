#!/usr/bin/env python3
import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests
import time


# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))

LEARNING_RATE = 1e-4
KEEP_PROB = 0.8
batch_size = 8
epochs = 30


def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    # TODO: Implement function
    #   Use tf.saved_model.loader.load to load the model and weights
    vgg_tag = 'vgg16'
    vgg_input_tensor_name = 'image_input:0'
    print(vgg_input_tensor_name)
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    vgg_layer7_out_tensor_name = 'layer7_out:0'

    tf.saved_model.loader.load(sess, [vgg_tag], vgg_path) # Load the VGG graph from file

    graph = tf.get_default_graph() # Grap the graph and for that grapg, grap each variable by name
    input_image = graph.get_tensor_by_name(vgg_input_tensor_name)
    keep_prob = graph.get_tensor_by_name(vgg_keep_prob_tensor_name)
    vgg_layer3_out = graph.get_tensor_by_name(vgg_layer3_out_tensor_name)
    vgg_layer4_out = graph.get_tensor_by_name(vgg_layer4_out_tensor_name)
    vgg_layer7_out = graph.get_tensor_by_name(vgg_layer7_out_tensor_name)
    
    return input_image, keep_prob,  vgg_layer3_out,  vgg_layer4_out,  vgg_layer7_out
tests.test_load_vgg(load_vgg, tf)


def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer3_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer7_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    # TODO: Implement function

    # This is where we create the architecture (Main part of project). We already have the encoder part based on vgg.
    # We extract layers 3, 4 and 7 to create skip layers from 3 and 4 and upsample from layer 7 
    # as per https://people.eecs.berkeley.edu/~jonlong/long_shelhamer_fcn.pdf 

    # 1x1 convolution for layer 7 from vgg
    layer7_conv_1x1 = tf.layers.conv2d(
    	vgg_layer7_out, 
    	num_classes, 
    	kernel_size=1, 
    	strides=1,
    	padding="same",
    	kernel_initializer= tf.random_normal_initializer(stddev=0.01), 
    	kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-5))

    deconv_layer1 = tf.layers.conv2d_transpose(
    	layer7_conv_1x1, 
    	num_classes, 
    	kernel_size=4, 
    	strides=2,
    	padding="same", 
    	kernel_initializer= tf.random_normal_initializer(stddev=0.01),
    	kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-5)) # Stride amount is cause upsampling by 2

    # 1x1 convolution for layer 4 from vgg
    layer4_conv_1x1 = tf.layers.conv2d(
    	vgg_layer4_out,
    	num_classes,
    	kernel_size=1,
    	strides=1,
    	padding="same",
    	kernel_initializer= tf.random_normal_initializer(stddev=0.01),
    	kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-5))

    # Adding deconvolved layer 1 and layer 4 for first skip connection.
    skip_connection1 = tf.add(layer4_conv_1x1, deconv_layer1)
    
    # 1x1 convolution for layer 3 for skip connection 2
    layer3_conv_1x1 = tf.layers.conv2d(
    	vgg_layer3_out,
    	num_classes,
    	kernel_size=1,
    	strides=1,
    	padding="same",
    	kernel_initializer= tf.random_normal_initializer(stddev=0.01),
    	kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-5))

    deconv_layer2 = tf.layers.conv2d_transpose(
    	skip_connection1,
    	num_classes,
    	kernel_size=4,
    	strides=2,
    	padding="same",
    	kernel_initializer= tf.random_normal_initializer(stddev=0.01),
    	kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-5))

    # Second skip connection made up of second deconvolution layer and 1x1 convolution of layer 3
    skip_connection2 = tf.add(deconv_layer2, layer3_conv_1x1)

    deconv_output_layer = tf.layers.conv2d_transpose(
    	skip_connection2,
    	num_classes,
    	kernel_size=16,
    	strides=8,
    	padding="same",
    	kernel_initializer= tf.random_normal_initializer(stddev=0.01),
    	kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-5))

    return deconv_output_layer
tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    # TODO: Implement function

    # logits and labels are now 2D tensors where each row represents a pixel and each column a class
    logits = tf.reshape(nn_last_layer, (-1, num_classes))
    correct_label = tf.reshape(correct_label, (-1, num_classes))

    # Computes softmax cross entropy between logits and labels
    cross_entropy_logits = tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=correct_label)

    # Computes the mean of elements across dimensions of a tensor
    cross_entropy_loss = tf.reduce_mean(cross_entropy_logits)

    optimizer = tf.train.AdamOptimizer(learning_rate)

    # Minimizes loss by combining calls compute_gradients() and apply_gradients(). 
    train_op = optimizer.minimize(cross_entropy_loss)

    return logits, train_op, cross_entropy_loss
tests.test_optimize(optimize)


def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    # TODO: Implement function
    
    total_loss = []


    for epoch in range(epochs):

    	start_time = time.time()
    	loss = None

    	for image, label in get_batches_fn(batch_size):

    		# Train and compute the loss
    		_, loss = sess.run(
    			[train_op, cross_entropy_loss],
    			feed_dict = {input_image: image,
    						correct_label: label,
    						keep_prob: KEEP_PROB,
    						learning_rate: LEARNING_RATE})
    		total_loss.append(loss)

    	print("[Epoch: {0}/{1} Loss: {2:4f} Time: {3}]".format(epoch + 1, epochs, loss, str(time.time() - start_time)))

    end_time = time.time() - start_time

tests.test_train_nn(train_nn)


def run():
    num_classes = 2
    image_shape = (160, 576)
    data_dir = './data'
    runs_dir = './runs'
    tests.test_for_kitti_dataset(data_dir)

    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(data_dir)
 
    # OPTIONAL: Train and Inference on the cityscapes dataset instead of the Kitti dataset.
    # You'll need a GPU with at least 10 teraFLOPS to train on.
    #  https://www.cityscapes-dataset.com/

    with tf.Session() as sess:

        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)

        # OPTIONAL: Augment Images for better results
        #  https://datascience.stackexchange.com/questions/5224/how-to-prepare-augment-images-for-neural-network

        # TODO: Build NN using load_vgg, layers, and optimize function
        input_image, keep_prob,  vgg_layer3_out,  vgg_layer4_out,  vgg_layer7_out = load_vgg(sess, vgg_path)

        # TODO: Train NN using the train_nn function
        deconv_output_layer = layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes)

        correct_label = tf.placeholder(dtype=tf.float32, shape=(None, None, None, num_classes), name="correct_label")
        # learning_rate = .0001
        learning_rate = tf.placeholder(dtype=tf.float32, name='learning_rate')

        logits, train_op, cross_entropy_loss = optimize(deconv_output_layer, correct_label, 
        														learning_rate, num_classes)

        sess.run(tf.global_variables_initializer())

        print("Staring Training...")

        train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
            	 correct_label, keep_prob, learning_rate)

        # TODO: Save inference data using helper.save_inference_samples
        #  helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob, input_image)
        helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob, input_image)
        # OPTIONAL: Apply the trained model to a video


if __name__ == '__main__':
    run()
