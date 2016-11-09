# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================


"""Utilities for parsing PTB text files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import os
import code
import tensorflow as tf


def _read_words(filename):
  with tf.gfile.GFile(filename, "r") as f:
    return f.read().decode("utf-8").replace("\n", "<eos>").split()


def _build_vocab(filename):
  data = _read_words(filename)

  counter = collections.Counter(data)
  count_pairs = sorted(counter.items(), key=lambda x: (-x[1], x[0]))

  words, _ = list(zip(*count_pairs))
  word_to_id = dict(zip(words, range(len(words))))

  return word_to_id


def _file_to_word_ids(filename, word_to_id):
  data = _read_words(filename)
  return [word_to_id[word] for word in data if word in word_to_id]


def ptb_raw_data(data_path=None):
  """Load PTB raw data from data directory "data_path".

  Reads PTB text files, converts strings to integer ids,
  and performs mini-batching of the inputs.

  The PTB dataset comes from Tomas Mikolov's webpage:

  http://www.fit.vutbr.cz/~imikolov/rnnlm/simple-examples.tgz

  Args:
    data_path: string path to the directory where simple-examples.tgz has
      been extracted.

  Returns:
    tuple (train_data, valid_data, test_data, vocabulary)
    where each of the data objects can be passed to PTBIterator.
  """

  train_path = os.path.join(data_path, "ptb.train.txt")
  valid_path = os.path.join(data_path, "ptb.valid.txt")
  test_path = os.path.join(data_path, "ptb.test.txt")

  word_to_id = _build_vocab(train_path)
  train_data = _file_to_word_ids(train_path, word_to_id)
  valid_data = _file_to_word_ids(valid_path, word_to_id)
  test_data = _file_to_word_ids(test_path, word_to_id)
  vocabulary = len(word_to_id)
  return train_data, valid_data, test_data, vocabulary


def ptb_producer(raw_phrase_data, raw_caption_data, phrase_count, num_steps, lexDim, name=None):
  """Iterate on the raw PTB data.

  This chunks up raw_data into batches of examples and returns Tensors that
  are drawn from these batches.

  Args:
    raw_data: one of the raw data outputs from ptb_raw_data.
    phrase_count: int, the phrase count.
    num_steps: int, the number of unrolls.
    name: the name of this operation (optional).

  Returns:
    A pair of Tensors, each shaped [phrase_count, num_steps]. The second element
    of the tuple is the same data time-shifted to the right by one.

  Raises:
    tf.errors.InvalidArgumentError: if phrase_count or num_steps are too high.
  """
  with tf.name_scope("PTBProducer"):
    raw_phrase_data = tf.convert_to_tensor(raw_phrase_data, name="raw_data", dtype=tf.int32)
    data_len = tf.size(raw_phrase_data)
    batch_len = data_len // (phrase_count)
    #batch_len = data_len // (num_steps * lexDim)
    #data = tf.reshape(raw_phrase_data[0 : phrase_count * batch_len],
    #                  [phrase_count, batch_len])
    data = tf.reshape(raw_phrase_data[0 : phrase_count * batch_len],
                      [num_steps, lexDim])
    #epoch_size = (batch_len - 1) // num_steps
    epoch_size = (data_len) // (batch_len) // phrase_count
    assertion = tf.assert_positive(
        epoch_size,
        message="epoch_size == 0, decrease phrase_count or num_steps")
    with tf.control_dependencies([assertion]):
      epoch_size = tf.identity(epoch_size, name="epoch_size")

    raw_caption_data = tf.convert_to_tensor(raw_caption_data, name="raw_captions", dtype=tf.int32)
    caption_data_len = tf.size(raw_caption_data)
    caption_batch_len = caption_data_len // num_steps
    #caption_data = tf.reshape(raw_caption_data[0: num_steps * caption_batch_len],
    #                          [num_steps, caption_batch_len])
    caption_data = tf.reshape(raw_caption_data[0: num_steps * caption_batch_len],
                              [num_steps * caption_batch_len])
    code.interact(local=dict(globals(), **locals()))                          
    #Iteratively dequeues integers in the range of iterations of an epoch 
    i = tf.train.range_input_producer(epoch_size, shuffle=False).dequeue()

    #Accesses data by slicing with the asynchronously updated epoch index
    #x = tf.slice(data, [0, i * num_steps], [phrase_count, num_steps])
    x = tf.slice(data, [0, i * num_steps], [num_steps, lexDim])
    #y = tf.slice(caption_data, [0, i * num_steps], [num_steps, lexDim])
    y = tf.slice(caption_data, [i * num_steps], [lexDim])

    print ("At reader")
    code.interact(local=dict(globals(), **locals()))
    return x, y, epoch_size