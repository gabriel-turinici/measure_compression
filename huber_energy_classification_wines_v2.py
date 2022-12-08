# -*- coding: utf-8 -*-
"""
Created on Wed Dec  7 13:56:41 2022

based on 
https://www.kaggle.com/code/lovelyrowlet/cluster-analysis-of-wine-dataset

Computes, by minimizing the Huber-energy distance, a clustering by quantizing
the distribution of the wines characteristics; the quantization is done 
with 3 points and 3 variable weights.

@author: Gabriel Turinici
"""

# Import libraries
import numpy as np  
import pandas as pd  
import seaborn as sns
import requests
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn import metrics
from sklearn.cluster import KMeans
import sys
from os import path
from scipy.optimize import differential_evolution, OptimizeResult 


nr_args=len(sys.argv)
arg_list=sys.argv



# Getting Data
namesList = ['category','Alcohol','Malic_Acid','Ash','Ash_Alcanity','Magnesium',
             'Total_Phenols','Flavanoids','Nonflavanoid_Phenols',
             'Proanthocyanins','Color_Intensity','Hue','OD280','Proline']


filename='italian_wines.csv'
#test if files are already available, and in this case just load them
#otherwise download from internet and save them

if(path.isfile(filename)):
    print('loading from file')
else:
    print('Load data from internet')
    data_url='https://archive.ics.uci.edu/ml/machine-learning-databases/wine/wine.data'
    print('Download Starting...')
    r = requests.get(data_url)
    with open(filename,'wb') as output_file:
        output_file.write(r.content)
    print('Download Completed!!!')


data = pd.read_csv('italian_wines.csv',index_col=False,header=None,names=namesList)
print('data lenght=',len(data))
original_data=data.copy()
#data.columns = namesList
data.head()

print('select only columns without category') 
data_no_cat= data[data.columns[1:]]
data_cat= data[['category']]

#kaggle file :
#data = pd.read_csv('/kaggle/input/wine-dataset-for-clustering/wine-clustering.csv')
data.describe()

# Viewing Information of Data
data.info()
observing_data_structure=False
if(observing_data_structure):
    sns.set(style='darkgrid', font_scale=1.3, rc={'figure.figsize': (25, 25)})
    ax = data.hist(bins=20, color='brown')

data_standardization=True
if(data_standardization):
    print('Data standardization')
    sc = StandardScaler()
    data_stand = sc.fit_transform(data_no_cat)
    print(data_stand)
    np.savez("wines_data_as_loaded",data,data_no_cat,data_cat,data_stand)

view_after_stand=False
if(view_after_stand):
    print('viewing Information of Data after standardization')
    sns.set(style='darkgrid', font_scale=1.3, rc={'figure.figsize': (25, 25)})
#    sns.set(style='darkgrid', font_scale=1.3, rc={'figure.figsize': (25, 25)})
    ax = pd.DataFrame(data_stand).hist(bins=20, color='brown')



k_means_clustering=True
if(k_means_clustering):
    print('K-means clustering')
    
    kmeans = KMeans(n_clusters=3, init='k-means++', random_state=42)
    y_kmeans = kmeans.fit_predict(data_stand)
    print('predicted k means=',y_kmeans)
    
    plt.figure('kmeans',figsize=(10, 6), dpi=80)
    plt.scatter(data_stand[:, 0], data_stand[:, 1], c=y_kmeans, s=50, 
                cmap='viridis')
    
    centers = kmeans.cluster_centers_
    kmeans_labels = kmeans.labels_
    score = metrics.silhouette_score(data_stand, kmeans_labels, metric="euclidean")
    score1 = metrics.calinski_harabasz_score(data_stand, kmeans_labels)
    score2 = metrics.davies_bouldin_score(data_stand, kmeans_labels)
    print("S C: ", score)
    print("CHI: ", score1)
    print("DBI: ", score2)
    plt.scatter(centers[:, 0], centers[:, 1], c='red', marker='x', s=200, alpha=0.5)
    plt.show()
    np.savez("kmeans_result",centers,kmeans_labels,score,score1,score2)

##############start compression in 3 clusters
J,N=data_stand.shape
K=3


#%%
#####################################
#     
#approach: stochastic optimization
#
#####################################
differential_evolution_version=False
differential_evolution_version=True



def empirical_radon_sbolev_distance_sq(X,Y,alphas,betas):
    '''
    Parameters
    ----------
    X :  NxK numpy array
        input data sample, each column a vector of dimension N, notation X_k
    Y : NxJ numpy array same as X for the second distribution
    alphas : 1D array of weights for X
    betas : same as alphas for Y 

    N = ambient dimension
    K = number of samples for X
    J = number of samples for Y
    
    Returns
    -------
    Radon-Sobolev distance
    
    '''
    
    assert (X.ndim==2) & (Y.ndim==2) & (alphas.ndim==1) & (betas.ndim==1), \
        "invalid input dimensions, shapes="+str(X.shape)+str(Y.shape)+\
            str(alphas.shape)+str(betas.shape)
    N,K=X.shape
    Ny,J=Y.shape
    Ka,=alphas.shape
    Jb,=betas.shape
#    print('shapes=',X.shape,Y.shape,alphas.shape,betas.shape)
    assert (N==Ny)& (K==Ka)&(J==Jb), 'invalid input dimensions'
#   print('mass diff=',np.sum(alphas)-np.sum(betas))
#   assert np.abs(np.sum(alphas)-np.sum(betas))<1.e-12,'incompatible masses'
#    print('alpha=',alphas)
    #construct big matrix
    points=np.concatenate((X,Y),axis=1)
    gammas=np.concatenate((alphas,-betas))
    #construct the distances matrix as a K+J x K+J matrix
    distZZ = np.linalg.norm(points[:,:,None]-points[:,None,:],ord=2,axis=0)
    
    return -0.5*gammas@distZZ@gammas

if(differential_evolution_version):
    def distance(params):
        '''
        This is a wrapper for 
        empirical_radon_sbolev_distance_sq(points,alphas=None):
    
        Parameters
        ----------
        params= a 1D array
         contains 'points' -first N*K values and 'alphas' next K values 
         as in empirical_radon_sbolev_distance_sq
        Returns
        -------
        distance squared
        '''
        
        X=params[0:N*K].reshape(N,K)
        alphas=params[N*K:(N+1)*K]
        alphas=alphas/np.sum(alphas)
        Y = data_stand.T
        betas=np.ones((J,))/J
        return empirical_radon_sbolev_distance_sq(X,Y,alphas,betas)
    
    def printCurrentIteration(xk,convergence=0.0):
        print('finished iteration, current value=')
        np.set_printoptions(suppress=True)
    #    print(list(xk))
        print(convergence)
        fval=distance(xk)
        print('fval=',fval)
        sys.stdout.flush()
        sys.stderr.flush()
    
    #fill in bounds: N*K bounds between -10 and + 10, other K between 0 and 1                                                        
    
    #bound_values=[(a,b) for a,b in zip(-1.5*np.min(data_stand,axis=0),1.5*np.max(data_stand,axis=0))]
    bound_values=list( ((np.min(data_stand),np.max(data_stand)),)*(N*K))
    bounds=bound_values+list(((0,1.),)*K)
    
    new_optimization=True#choose if to optimize again or just use previous results
    
    if new_optimization:
    
        if(nr_args >= 2):# first argument after script name is number of workers
            print(arg_list[1])
            allowed_workers = int(arg_list[1])
        else:
            allowed_workers=-1
        print('will use',allowed_workers,' parallel workers')
        sys.stdout.flush()
        sys.stderr.flush()

        result = differential_evolution(distance, bounds,disp=True,
                                      maxiter=100,
                                      callback=printCurrentIteration)
            
#        result = differential_evolution(distance, bounds,disp=True,
#                                      maxiter=10,workers=allowed_workers,
#                                      callback=printCurrentIteration)
        print(result)

    else:
      result=OptimizeResult(x= np.array([]))

#exploit results
X_opt=result.x[0:N*K].reshape(N,K)
alphas_opt=result.x[N*K:(N+1)*K]
alphas_opt=alphas_opt/np.sum(alphas_opt)
n_opt=alphas_opt*J
print('n_opt=',n_opt)

print('attributing labels')

#compute all pairwise distances
dist_center_points = np.linalg.norm(X_opt[:,:,None]-data_stand.T[:,None,:],ord=2,axis=0)
quantization_labels= np.argmin(dist_center_points,axis=0)

sns.set(style='white', font_scale=1.3, rc={'figure.figsize': (25, 25)})
plt.figure('quantization categories',figsize=(10, 6), dpi=80)
plt.scatter(data_stand[:, 0], data_stand[:, 1], c=quantization_labels, s=40, 
            cmap='viridis')#viridis ,marker=['o','x','d']
plt.scatter(X_opt[0, :], X_opt[1, :], c='green', marker='^', s=200, alpha=0.5)
plt.scatter(centers[:, 0], centers[:, 1], c='red', marker='s', s=200, alpha=0.5)
plt.tight_layout()
plt.legend(["Data", "quantization points","K means centers"])
plt.title('Weights : '+str(np.round(alphas_opt[0],2)) +", "
        +str(np.round(alphas_opt[1],2))+", "+str(np.round(alphas_opt[2],2))
                               )
plt.show()
plt.savefig("quantization_wines.pdf")

#len(quantization_labels[quantization_labels==1])
#np.bincount(quantization_labels)
confusion_d_q=metrics.confusion_matrix(data_cat, quantization_labels+1)
confusion_k_q=metrics.confusion_matrix(quantization_labels, kmeans_labels)

#resultat: same as kmeans in this case

np.savez("wines_results", X_opt,alphas_opt,n_opt,nfev=result.nfev,
         nit=result.nit,fun=result.fun,confusion_d_q=confusion_d_q,
         confusion_k_q=confusion_k_q)