import numpy as np, trimesh, time
from scipy import ndimage as nd
from skimage.measure import marching_cubes
t=time.time()
m=trimesh.load('orig_clean.ply',process=False)
h=0.0028; r=2.5   # voxel (~1.3 mm at 0.45 m) and closing radius in voxels
# vertices plus face centroids: the surface is dense enough that this marks every crossed voxel
P=np.vstack([m.vertices, m.triangles_center])
lo=m.bounds[0]-6*h; shape=np.ceil((m.bounds[1]-lo)/h).astype(int)+6
idx=np.floor((P-lo)/h).astype(int); occ=np.zeros(shape,bool); occ[idx[:,0],idx[:,1],idx[:,2]]=True
print('grid',shape,'occupied',occ.sum(),round(time.time()-t),flush=True)
dil=nd.distance_transform_edt(~occ)<=r
lab,_=nd.label(~dil); border=np.unique(np.concatenate([lab[0].ravel(),lab[-1].ravel(),lab[:,0].ravel(),lab[:,-1].ravel(),lab[:,:,0].ravel(),lab[:,:,-1].ravel()]))
outside=np.isin(lab,border[border>0])
solid=~outside
sd=nd.distance_transform_edt(solid)-nd.distance_transform_edt(~solid)   # >0 inside
sd=nd.gaussian_filter(sd,0.6)
v,f,_,_=marching_cubes(sd,r,spacing=(h,h,h)); v+=lo
o=trimesh.Trimesh(v,f,process=True)
cc=sorted(o.split(only_watertight=False),key=lambda c:len(c.faces))
o=trimesh.util.concatenate([c for c in cc if len(c.faces)>500])
print('faces',len(o.faces),'watertight',o.is_watertight,'parts',len([c for c in cc if len(c.faces)>500]),'bounds',o.bounds.round(4),round(time.time()-t),flush=True)
o.export('closed.ply')
