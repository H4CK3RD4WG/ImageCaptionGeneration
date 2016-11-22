'''
gotta be bad to get good
'''

from __future__ import print_function

import densecap_processing as dp
import reader

import tensorflow as tf
from tensorflow.python.ops import rnn, rnn_cell
from tensorflow.contrib.slim.python.slim import evaluation

import numpy as np
#from nltk import bleu_score
import code
import matplotlib.pyplot as plt


# To make input, we need to create a tensor
# Our tensor will include:
# -Vector for each phrase in an image
# -Higher dimensional representation of number of words in each sequence
# -Vector representation of each word

class NetworkInput(object):

    @property
    def phrases(self):
        return self.phrase_batch
    @phrases.setter
    def phrases(self, value):
        self.phrase_batch = value

    @property
    def captions(self):
        return self.caption_batch
    @captions.setter
    def captions(self, value):
        self.caption_batch = value

    def __init__(self, batchSize, phraseCount, phraseDim, wordDim, phraseBatch, captionBatch, numEpochs, epochSize):
        self.phrase_count = phraseCount
        self.phrase_dimension = phraseDim
        self.word_dimension = wordDim
        #self.inputs = [np.asarray(inputs[0], dtype=np.float32), 
        #               np.asarray(inputs[1], dtype=np.float32)] 
        self.batch_size = batchSize
        self.num_epochs = numEpochs
        self.epoch_size = epochSize
        self.phrase_batch = phraseBatch
        self.caption_batch = captionBatch
        
class NetworkParameters(object):
    def __init__(self, layerSize, numLayers, learningRate, initScale):
        self.layer_size = layerSize
        self.num_layers = numLayers
        self.learning_rate = learningRate
        self.data_type = tf.float32
        self.init_scale = initScale

class NetworkResults(object):
    def __init__(self, displayStep):
        self.costHistory = {}
        self.display_step = displayStep

    def record_point(self, key, val):
        self.costHistory[key] = val
        
    def plot_results(self):
        plt.plot(self.costHistory.keys(), self.costHistory.values())
        plt.xticks(np.arange(min(self.costHistory.keys()), 
                             max(self.costHistory.keys()), self.display_step))
        plt.xlabel('epochs')
        plt.ylabel('cost')
        plt.tick_params(axis='both', which='major', labelsize=8)
        plt.tick_params(axis='both', which='minor', labelsize=8)
        plt.show()
        

class LSTMNet(object):

    @property
    def inputs(self):
        return self._input

    @property
    def parameters(self):
        return self._parameters

    @property
    def results(self):
        return self._results

    @property
    def log_path(self):
        return "results/log"

    @property
    def global_step(self):
        return self.globalStep

    @property
    def model(self):
        return self._model

    @property
    def initial_state(self):
        return self._initial_state

    @property
    def _x(self):
        return self.placeholder_x

    @property
    def _y(self):
        return self.placeholder_y

    @property
    def cost(self):
        return self._cost

    @property
    def final_state(self):
        return self._final_state

    @property
    def probabilities(self):
        return self._probs

    @property
    def optimizer(self):
        return self._optimizer

    @property
    def train_op(self):
        return self._train

    @property
    def decoder(self):
        return self._decoder

    @property
    def encoder(self):
        return self._encoder

    #@property 
    #def training_iterations(self):
    #    return self.inputs.data_size / self.inputs.batch_size
    def training_iterations(self, session):
        return self.inputs.epoch_size.eval(session=session)

    def __init__(self, inputs, params, results, codex):
        with tf.variable_scope("Model", reuse=None):

            #Add network parameters objects
            self._input = inputs
            self._parameters = params
            self._results = results

            self._decoder = codex[0]
            self._encoder = codex[1]

            self.epochs = 0
            self.epoch_iteration = 0

            #####################Build the LSTM network#############################

            with tf.variable_scope("Inputs"):
                self.placeholder_x = tf.placeholder_with_default(
                    self.inputs.phrases, self.inputs.phrases.get_shape())
                self.placeholder_y = tf.placeholder_with_default(
                    self.inputs.captions, self.inputs.captions.get_shape()) 
                    
            #Embedding layer transforms one-hot vectors to real-valued inputs for learning
            #Necessary for later matmul computations anyways

            with tf.variable_scope("Embedding_Layer"):
                with tf.device("/cpu:0"):
                    #embedding = tf.get_variable("embedding", 
                    #        [inputs.phrase_dimension, params.layer_size], dtype=params.data_type)
                    
                    #Make embedding[inputs.word_dimension, params.layer_size] 
                    #Split input along phrase dimension for [batch_size, word_dimension]
                    #matmul by embeddings to get [batch_size, params.layer_size]

                    embedding = tf.get_variable("embedding", 
                            [inputs.word_dimension, params.layer_size], dtype=params.data_type)

                    phraseEmbedding = tf.nn.embedding_lookup(embedding, self._x)
                code.interact(local=dict(globals(), **locals()))
                phraseEmbedding = [tf.squeeze(input_step, [1])
                    for input_step in tf.split(1, inputs.phrase_dimension, phraseEmbedding)]
            
            #Is this complete nonsense? Investigate the 'linear' function 
            #that makes us use 2D tensors as input to the RNN
                #phraseEmbedding = [tf.reshape(input_step, [-1, params.layer_size])
                #    for input_step in phraseEmbedding]
                #phraseEmbedding = [tf.reshape(input_step, [inputs.batch_size, -1])
                #    for input_step in phraseEmbedding]
            
            '''hidden_weights = tf.Variable(
                tf.random_normal([inputs.word_dimension, params.layer_size]))
            hidden_input = tf.matmul(self._x, hidden_weights)
            
            phraseEmbedding = [tf.squeeze(input_step, [1])
                               for input_step in tf.split(
                                       1, inputs.phrase_dimension, hidden_input)]'''
            
            # Define an lstm cell with tensorflow
            lstm_cell = rnn_cell.BasicLSTMCell(
                params.layer_size, forget_bias=1.0, state_is_tuple=True)
            layer_cell = rnn_cell.MultiRNNCell(
                [lstm_cell] * params.num_layers, state_is_tuple=True)

            #self._initial_state = layer_cell.zero_state(
            #        inputs.word_dimension, params.data_type)
            #self._initial_state = layer_cell.zero_state(
            #        inputs.batch_size * inputs.word_dimension, params.data_type)
            self._initial_state = layer_cell.zero_state(
                    inputs.batch_size, params.data_type)

            code.interact(local=dict(globals(), **locals()))
            outputs, state = rnn.rnn(
                layer_cell, phraseEmbedding, 
                initial_state = self._initial_state, dtype=params.data_type)

            #outputs, state = rnn.rnn(
             #   layer_cell, phraseEmbedding, 
              #    dtype=params.data_type)
            
            code.interact(local=dict(globals(), **locals()))
            #Concatenate MultiRNN output states to create Output layer
            with tf.variable_scope("Output_Layer"):
                output = tf.reshape(tf.concat(1, outputs), [-1, params.layer_size])
                self._final_state = state
                
                with tf.variable_scope("Squash"):
                    # Randomly initializing weights and biases ensures feature differentiation
                    #weights = tf.Variable(tf.random_normal([params.layer_size, 1]))
                    
                    weights = tf.Variable(tf.random_normal(
                        [params.layer_size, inputs.word_dimension]))
                    biases = tf.Variable(tf.random_normal([inputs.word_dimension]))

                    self._model = tf.matmul(output, weights) + biases

                    #prod = tf.matmul(output, weights)
                    #self._model = tf.reshape(
                    #    prod, [inputs.phrase_dimension, inputs.word_dimension]) + biases 
                    
                    #self._model = tf.reshape(prod, 
                    #[inputs.batch_size, inputs.phrase_dimension, inputs.word_dimension]) + biases 
                    
                    #self.probabilities is the final layer of the network
                    #squash all predictions into range 0->1 for sane inference 
                    self._probs = tf.nn.softmax(self._model)

                with tf.variable_scope("Backpropagation"):
                    #self._cost = tf.reduce_mean(
                    #    tf.nn.softmax_cross_entropy_with_logits(self._model, self._y))
                    
                    logits = [self._model]
                    targets = [tf.reshape(self._y, [-1])]
                    weights = [tf.ones([inputs.batch_size * inputs.phrase_dimension], 
                         dtype=params.data_type)]

                    self._cost = tf.reduce_mean(
                        tf.nn.seq2seq.sequence_loss(logits,targets,weights)) / inputs.batch_size
                    
                    code.interact(local=dict(globals(), **locals()))
                    #I don't know what this does. Some variant of backpropagation
                    self.globalStep = tf.Variable(0, name='global_step', trainable=False)
                    self._optimizer = tf.train.AdamOptimizer(
                        learning_rate=params.learning_rate).minimize(
                            self._cost, global_step=self.globalStep)

    def train_network(self):
        initializer = tf.initialize_all_variables()
        #initializer=tf.random_uniform_initializer(-self.parameters.init_scale, 
        ###                                          self.parameters.init_scale)
        #Supervisor does nice things, like start queues
        saves = tf.train.Saver(write_version=tf.train.SaverDef.V2)
        sv = tf.train.Supervisor(logdir=self.log_path, saver=saves, 
                                 global_step=self.global_step, save_model_secs=1)      
        with sv.managed_session() as session:
            session.run(initializer)
            while self.epochs <= self.inputs.num_epochs:
                self.run_epoch(session)
                #print(self.sample(session))  # -- get caption
        self.results.plot_results()

    def run_epoch(self, session):
        """Runs the model on the given data."""
        costs = 0.0
        state = session.run(self.initial_state)
        fetches = {"cost": self.cost, "final_state": self.final_state, 
                       "eval_op":self.optimizer}
        print ("Epoch: ", self.epochs)
        for step in range(self.training_iterations(session)):
            train_dict = {}
            for i, (c, h) in enumerate(self.initial_state):  
                train_dict[c] = state[i].c
                train_dict[h] = state[i].h
            #code.interact(local=dict(globals(), **locals()))
            
            vals = session.run(fetches, train_dict)
             
            cost = vals["cost"]
            state = vals["final_state"]
            costs += cost
        print ("Cost: ", costs)
        if self.epochs % self.results.display_step == 0:
            self.results.record_point(self.epochs, costs)
        self.epochs += 1
        
        return np.exp(costs)

    def sample(self, session, seed = '\''):
        state = session.run(self.initial_state)  
        ret = seed
        char = ret

        x = np.zeros((self.inputs.phrase_dimension, self.inputs.word_dimension))
        #x[0, 0] = self.encoder[char]
        #code.interact(local=dict(globals(), **locals()))
        #feed = {self._x: x, self.initial_state:state}
        #[state] = session.run([self.final_state], feed)

        #Seed state is trained network on <START> = '\''
        num = self.inputs.phrase_dimension #For now, fixed length captions
        for n in range(num):              #Ideally this loop is 'until generate <STOP>'
            x = np.zeros((self.inputs.phrase_dimension, self.inputs.word_dimension))
            #x[0, 0] = self.encoder[char]
            feed = {self._x: x, self.initial_state:state}

            [probs, state] = session.run([self.probabilities, self.final_state], feed)
            p = probs[n]                #We only sample the next word in the sequence   
            sample = np.argmax(p)          #We can write more complicated sampling functions
            pred = self.decoder[sample]
            ret += pred
            char = pred
            #code.interact(local=dict(globals(), **locals()))
        return ret
        
