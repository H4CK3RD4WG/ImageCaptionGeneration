# Output of densecap is a JSON string containing phrases and boxes and importance scores
# boxes are given as xy coordinate of upper left corner and width/height
# We want to give an id to every phrase, box and score, and store each in a dictionary

from pycocotools.coco import COCO
import json as js
import numpy as np
import subprocess
import re
import math
import os
import code

import salience

annFile = 'annotations/captions_train2014.json'
coco = COCO(annFile)

START = '\''
STOP = '.'

############################### MS COCO PROCESSING #####################################

#Get some number of imgIDs from MS-COCO
def get_coco_imgs(number):
    imgIDs = sorted(coco.getImgIds())
    numImages = imgIDs[:number]
    return numImages
    
#Retrieves set of captions for a set of image Ids from MS-COCO
def coco_to_captions(imgIDs):
    numAnnIDs = coco.getAnnIds(imgIDs)
    return coco.loadAnns(numAnnIDs)

#Returns a single caption associated with each image from the set of annotations
#images have multiple captions which we may be able to take advantage of later
#We also add <START> and <STOP> symbols - we use escaped characters \' and \" respectively
def get_coco_captions(_captions, caption_count=1):
    capDict = {}
    for x in _captions:
        if not x['image_id'] in capDict:
            capDict[x['image_id']] = [START + x['caption']]
        elif len(capDict[x['image_id']]) < caption_count:
            capDict[x['image_id']].append(START + x['caption'])
    return capDict

#Returns a sorted list of unique words from the set of annotations
def get_coco_lexicon(_captions):
    words = []
    for x in _captions:
        for word in re.split('[(\'\.)\s,]', x['caption']):
            words.append(word)
    return sorted(set(words))

################################# DENSECAP PROCESSING ###########################################
#Still assumes densecap is in the folder next to ImageCaptionGeneration
#/densecap
#/ImageCaptionGeneration
#    /annotations <= contains MS-COCO 2014 annotations
#    /images <= contains MS-COCO 2014 training images
#    /densecap_images <= input dir to densecap processing
#    /results
#        /boxes <= holds visually annotated images after densecap

# TAKES SET OF IMAGE IDs FROM MS COCO

#Automatically executes densecap on a set of image Ids from MS-COCO
#automatically writes results to /results
#need to be in /densecap to execute "run_model.lua" because I can't figure
#out how to install lua modules. 
def coco_to_densecap(imgIDs):
    print "Cleaning processing folder..."
    deleteCommand = 'rm -rf densecap_images && mkdir densecap_images'
    subprocess.call(deleteCommand, shell=True)
    for x in imgIDs:
        command = 'cp images/COCO_train2014_%s.jpg densecap_images'%(str(x).zfill(12))
        print str(x) + " Executing: "+ command
        subprocess.call(command, shell=True)
    os.chdir("../densecap")
    dense_command = "th run_model.lua -input_dir ../ImageCaptionGeneration/densecap_images -output_vis_dir ../ImageCaptionGeneration/results -output_dir ../ImageCaptionGeneration/results/boxes -gpu -1"
    subprocess.call(dense_command, shell=True)
    os.chdir("../ImageCaptionGeneration")

#Used to retrieve densecap processing results
#Takes a path to _json filename. Should be "results/results.json" in the local directory.
def json_to_dict(_json):
    json = open(_json, 'r')
    result = js.load(json)
    return result

#parse densecap results for image info
def dict_to_imgs(_result):
    images = {}    
    count = 0
    for img in _result['results']:
        images[count] = img
        count = count + 1
    print "Counted %s images" % count
    return images

#takes image info to get various fields
def get_captions(_images, img_index):
    return _images[img_index]['captions']

def get_boxes(_images, img_index):
    return _images[img_index]['boxes']

def get_scores(_images, img_index):
    return _images[img_index]['scores']


######################### INPUT PREPROCESSING / WORD REPRESENTATION ####################

#Build 2-way lookup tables for encoding and decoding word representations in our neural net
def build_lookup_lexicon(_lexicon, index2word, word2index):
    count = 0;
    for x in _lexicon:
        index2word[count] = x
        word2index[x] = count
        count = count + 1
    # Add special symbols
    index2word[count] = START
    word2index[START] = count
    count = count + 1
    index2word[count] = STOP
    word2index[STOP] = count

def empty_one_hot_vector(lex_size):
    return [0] * lex_size    

#Takes a string and uses the lexicon to convert to a one-hot
#[0, ..., 1, ..., 0] vector representation of a word
def string_to_vector(word, invertDict):
    one_hot = empty_one_hot_vector(len(invertDict))  
    one_hot[invertDict[word]] = 1
    return one_hot

def vector_to_string(vector, wordDict):
    return wordDict[np.argmax(vector)]

def extract_phrase_vectors(phrase_count, phraseLength, imgCount, image_props, invertDict):
    one_hot_list = [[[[]] * phraseLength] * phrase_count] * imgCount
    for x in range(0, imgCount):
        salient = salience.salient_phrases(
            image_props, x, lambda: salience.k_top_scores(image_props[x], phrase_count))
        phraseI = 0
        for phrase in salient:
            count = 0
            #print ("Phrase ", phrase)
            for word in phrase.split():
                #print word
                if count >= phraseLength:
                    #print "Break phrase"
                    break
                elif word in invertDict:
                    #print "Add word"
                    one_hot_list[x][phraseI][count] = string_to_vector(word, invertDict)
                else:
                    #print "Fill void"
                    one_hot_list[x][phraseI][count] = empty_one_hot_vector(len(invertDict))
                #print count
                count = count + 1
            while count < phraseLength:  #Padding
                one_hot_list[x][phraseI][count] = empty_one_hot_vector(len(invertDict))
                count = count + 1
            #print count
            #print phraseI
            phraseI = phraseI + 1
    return one_hot_list

#Remember that one day we will need to generalize this yet again for captionCount
def extract_caption_vectors(phraseLength, imgCount, invertDict, captions):
    one_hot_list = [[[]] * phraseLength] * imgCount
    imgID = 0
    for cap in captions:
        for caption in captions[cap]:
            count = 0
            for word in re.split('[(\'\.\s)]', caption): 
                #print word
                if count >= phraseLength:
                    #print "break cap"
                    break
                elif word in invertDict:
                    #print "To one-hot"
                    one_hot_list[imgID][count] = (string_to_vector(word, invertDict))
                else:
                    #print "Caption split deviant"
                    one_hot_list[imgID][count] = (empty_one_hot_vector(len(invertDict)))
                count = count + 1
            while count < phraseLength:    #Padding
                one_hot_list[imgID][count] = (empty_one_hot_vector(len(invertDict)))
                count = count + 1
        imgID = imgID + 1
    return one_hot_list


