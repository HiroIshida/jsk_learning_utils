#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os,sys
import torch
import torchvision
import numpy as np
import matplotlib.pyplot as plt
import copy

from network import DCAE

from PIL import Image
import glob
from sklearn.model_selection import train_test_split
import pickle

class DCAErosbag(object):
    def __init__(self, epoch, model_dir, data_dir, z_dim):
        self.epoch = epoch
        self.model_dir = model_dir
        self.data_dir = data_dir
        self.z_dim = z_dim
        print("epoch:{}, model_dir:{}, z_dim:{}".format(self.epoch, self.model_dir ,self.z_dim))
        self.check_and_make_dir()
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        print("device:{}".format(self.device))
        self.net = DCAE(channel=3, height=224, width=224, z_dim=z_dim).to(self.device)
        print(self.net)

        self.data_preparation()
        
    def data_preparation(self):
        # データを読み込む
        
        print("load data from {}".format(self.data_dir))

        # load data from binary pickle file
        dump_file = self.data_dir + "images.txt"
        f = open(dump_file,'rb')
        frames = pickle.load(f)
        f.close
        dataset = []
        for img in frames:
            img = img.resize((224,224))
            img_tensor = torchvision.transforms.functional.to_tensor(img)
            dataset.append(img_tensor)
        print(len(dataset))
        trainset, testset = train_test_split(dataset)
        print(len(trainset),len(testset))
        self.trainloader = torch.utils.data.DataLoader(trainset,
                                                       batch_size=100,
                                                       shuffle=True)
        self.testloader = torch.utils.data.DataLoader(testset,
                                                      batch_size=100,
                                                      shuffle=False)
        # # load data from raw image
        # dataset = []
        # for img_path in glob.glob(os.path.join(self.data_dir, '*png')):
        #     img = Image.open(img_path)
        #     img = img.resize((224,224))
        #     img_tensor = torchvision.transforms.functional.to_tensor(img)
        #     dataset.append(img_tensor)
        # print(len(dataset))
        # trainset, testset = train_test_split(dataset)
        # print(len(trainset),len(testset))
        
        # self.trainloader = torch.utils.data.DataLoader(trainset,
        #                                                batch_size=100,
        #                                                shuffle=True)
        # self.testloader = torch.utils.data.DataLoader(testset,
        #                                               batch_size=100,
        #                                               shuffle=False)

    def check_and_make_dir(self):
        model_dir = self.model_dir
        if False == os.path.exists(model_dir):
            os.makedirs(model_dir)
            print("make dir in path: {}".format(model_dir))
        
    def save_model(self):
        model_path = self.model_dir + "model.pt"
        torch.save(self.net.to('cpu').state_dict(), model_path)
        print("model saved in {}".format(model_path))
        
    def train(self):
        optimizer = torch.optim.Adam(self.net.parameters())
        criterion = torch.nn.MSELoss()

        # train and val
        t_losses = []
        v_losses = []
        for e in range(self.epoch):
            # train
            losses = []
            self.net.train()
            for x in self.trainloader:
                x = x.to(self.device)
                optimizer.zero_grad()

                pred,z = self.net.forward(x)
                loss = criterion(x,pred)
                loss.backward()
                optimizer.step()

                losses.append(copy.deepcopy(loss.cpu().detach().numpy()))

            # val
            losses_val = []
            self.net.eval()
            for x in self.testloader:
                x = x.to(self.device)

                pred,z = self.net.forward(x)
                loss = criterion(x,pred)

                losses_val.append(copy.deepcopy(loss.cpu().detach().numpy()))

            t_loss = np.average(losses)
            v_loss = np.average(losses_val)
            t_losses.append(t_loss)
            v_losses.append(v_loss)
            print("EPOCH: %d Train Loss: %f Valid Loss: %f" % (e+1, t_loss, v_loss))

        fig = plt.figure()
        plt.plot(t_losses, label="train")
        plt.plot(v_losses, label="valid")
        log_path = self.model_dir + "log.png"
        plt.legend()
        fig.savefig(log_path)
        print("log image saved in {}".format(log_path))
        plt.show()
        plt.clf()

if __name__ == '__main__':
    epoch = int(sys.argv[sys.argv.index("-e") + 1]) if "-e" in sys.argv else 100
    z_dim = int(sys.argv[sys.argv.index("-z") + 1]) if "-z" in sys.argv else 50
    data_dir = sys.argv[sys.argv.index("-d") + 1] if "-d" in sys.argv else "data/from_rosbag/"
    if data_dir[-1:] != '/':
        data_dir += '/'
    model_dir = sys.argv[sys.argv.index("-m") + 1] if "-m" in sys.argv else "../models/rosbag_DCAE/"
    if model_dir[-1:] != '/':
        model_dir += '/'
    trainer = DCAErosbag(epoch, model_dir, data_dir, z_dim)
    trainer.train()
    trainer.save_model()
