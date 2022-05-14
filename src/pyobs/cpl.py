#!/bin/env python
"""
   Implements Python interface to the CPL L2 data.
"""

import os

import h5py
from   numpy    import ones, zeros, interp, NaN, isnan, array, ma
from   datetime import datetime, timedelta
from   types      import *

from matplotlib.pyplot import imshow, xlabel, ylabel, title, colorbar, \
                              gca, axes, figure, show
from matplotlib.colors import LogNorm

#.......................................................................
class CPL_L2(object):

      """Implements the CPL class."""


      def __init__ (self,cpl_filename,verbose=True,freq=3.0):
        """
        Creates an CPL object defining the following attributes:

             lon            ---  longitudes in degrees        (nobs)
             lat            ---  latitudes in degrees         (nobs)

        """

        self.verb = verbose

        # Get date from file name
        # -----------------------
        date = os.path.basename(cpl_filename).split('_')[2]
        year, month, day = int(date[0:4]), int(date[4:6]), int(date[6:8])
        
#       SDS to Keep
#       -----------
        SDS = (ATB_1064,
               ATB_355,
               ATB_532,
               Bin_Alt,
               Bin_Width,
               #Cali_1064,
               #Cali_355,
               #Cali_532,
               Date,
               Dec_JDay,
               Depol_Ratio,
               End_JDay,
               Frame_Top,
               Gnd_Hgt,
               Hori_Res,
               Latitude,
               Layer_Bot_Alt,
               Layer_Top_Alt,
               Layer_Type,
               Longitude,
               MaxLayers,
#               Mole_Back,
               NumBins,
               NumChans,
               NumLayers,
               NumRecs,
               NumWave,
               Plane_Alt,
               Plane_Pitch,
               Plane_Roll,
               Pressure,
               Project,
               RH,
               Saturate,
               Start_JDay,
               Temperature,
               )



        # Short names
        # -----------
        Short_Name = dict(
                      gps_alt = 'lev',
                     gps_date = 'date',
                      gps_lat = 'lat',
                      gps_lon = 'lon',
                      Midtime = 'time',
                    Altitudes = 'z',
                  DEM_gnd_alt = 'zs',
                     )

        Short_Name['O3_prfl'] = 'O3'
        Short_Name['Sa_532nm_prfl'] = 'lr_532'
        Short_Name['aerdep_532nm_prfl'] = 'dep_532'
        Short_Name['bsc_532nm_prfl'] = 'bsc_532'
        Short_Name['ext_532nm_prfl'] = 'ext_532'
                  
        # Open the CPL file and loop over the datasets,
        # extracting navigation and data
        # ----------------------------------------------
        f = h5py.File(cpl_filename,mode='r+')
        if self.verb:
           print("[] Opening CPL file <%s>"%cpl_filename)
        for sds in list(SDS.keys()):
          g = f.get(sds)
          for v in SDS[sds]:
            try:
              name = Short_Name[v]
            except:
              name = v
            if self.verb:
                  print("   + Reading <%s> as <%s>"%(v,name))
            data = g.get(v)
            self.__dict__[name] = data
  
        # Read data and make these numpy arrays
        # -------------------------------------
        self.lon  = self.lon[:].ravel()
        self.lat  = self.lat[:].ravel()
        self.z    = self.z[:].ravel()
        self.lev  = self.lev[:].ravel()
        self.time = self.time[:].ravel()

        self.nt = self.lat.shape[0]
        self.nz = self.z.shape[0]

        # Create datetime
        # ---------------
        t0 = datetime(year,month,day)
        self.Time = []
        for i in range(self.nt):
          dt = timedelta(seconds = int(self.time[i]) )
          self.Time += [t0 + dt,]
        self.Time = array(self.Time)
        self.tyme = self.Time
        
        # Find bracketing synoptic times
        # ------------------------------
        dt = timedelta(seconds=int(freq * 60. * 60.)) # 3 hour
        tmin, tmax = (self.Time[0], self.Time[-1]) 
        t_ = datetime(tmin.year,tmin.month,tmin.day)  # beg of day 
        s0 = int((tmin-t_).seconds / (freq*60*60) )   
        T  = t_ + s0 * dt                             # lower synoptic hour
        self.syn = [T,]
        while ( T<tmax ):
          T += dt
          self.syn += [ T, ]
        self.dt_syn = dt

        # Find time indices within synoptic brackets
        # ------------------------------------------
        self.IA = [] # index and weight for time interpolation
        for t in self.syn[:-1]:
          a = ones(self.nt)
          I = (a==1.)
          for n in range(self.nt):
             I[n] = (self.Time[n]>=t)&(self.Time[n]<t+self.dt_syn)
             a[n] = (self.Time[n] - t).seconds
          a = a / float(self.dt_syn.seconds) 
          self.IA += [(I,a),]
        
        # Save file handle for later
        # --------------------------
        self.h5 = f

#--
      def addVar(self,url,Vars=None,Verbose=True,Levels=None):
        """
        Sample variable along CPL track.
        """
        from grads import GrADS
        ga = GrADS(Window=False,Echo=False)
        fh = ga.open(url)
        if Levels is not None:
            ga('set lev %s'%Levels)

        if Vars is None:
            Vars = ga.query('file').vars
        elif type(Vars) is StringType:
            Vars = [Vars,]
        for var in Vars:
            if Verbose:
                print(' Working on <%s>'%var)
            q = ga.sampleXYT(var,self.lon,self.lat,self.tyme,Verbose=Verbose).data
            self.__dict__[var] = ma.MaskedArray(q,mask=q>=UNDEF)
#--

      def sampleExt(self,asm_Nv,aer_Nv,Levels='70 40',channels=(532,),I=None,vnames=None,Verbose=False):
        """
         Sample aerosol mixing ratio and perform Mie calculation returning

          (ext,sca,backscat,aback_sfc,aback_toa)

         On input, aer_Nv is the collection with the aerosol concentration;
         asm_Nv is the met collection containg the height field.

         This method implements a Mie calculator at obs location. An
         alternative is to use the off-line AOD 3D calculator and sample
         it at the lidar track with the addVar() method.
        """
        from mieobs import getAOPext

        # Sample aerosol concetration and Height
        # --------------------------------------
        self.addVar(aer_Nv,Levels=Levels)
        self.addVar(asm_Nv,Vars=('H',),Levels=Levels)

        # Handle GrADS/GFIO case inconsistency
        # ------------------------------------
        self.AIRDENS, self.DELP = self.airdens, self.delp
        if vnames is None:
            vnames = [ 'du001', 'du002', 'du003', 'du004', 'du005',
                       'ss001', 'ss002', 'ss003', 'ss004', 'ss005',
                       'bcphobic', 'bcphilic',
                       'ocphobic', 'ocphilic',
                       'so4' ]
        
        # Perform Mie calculation
        # -----------------------
        ext,sca,backscat,aback_sfc,aback_toa = \
        getAOPext(self,channels,I=None,vnames=vnames,Verbose=False)
     
#--
      def zInterp(self,v5):
            """Vertically interpolates the GEOS-5 variable v5
            to the CPL heights."""
            
            if len(v5.shape) != 2:
                  raise ValueError('variable to be interpolated must have rank 2')

            nt, nz = v5.shape
             
            if self.nt != nt:
                  raise ValueError('inconsistent time dimension')

            if self.H.shape[1] != nz:
                  raise ValueError('inconsistent GEOS-5 vertical dimension')

            v = ones((self.nt,self.nz)) # same size as CPL arrays
            for t in range(self.nt):
                  v[t,:] = interp(self.z,self.H[t,:],v5[t,:],left=NaN)

            return v

#--
      def curtain(self,v, tit=None, vmin=None, vmax=None,
                  mask=None, mask_as=None, Log=False,
                  ticks=None, format=None, lower=True):
            """Plots a 2D curtain plot."""

            v_ = v[:,:]
            if mask_as != None:
                  mask = isnan(mask_as[:,:])
            if mask != None:
                  v_[mask] = NaN

            z = self.z / 1000.

            # lower half of profile
            nz = self.nz
            if lower:
                  z = z[:nz/2]
                  v_ = v_[:nz/2,:]
                  aspect = 0.25
                  tweak = 0.4
            else:
                  aspect = 0.175
                  tweak = 0.16
                  
            t = self.time/3600.
            ext = ( t[0], t[-1], z[0], z[-1] )

            if vmin is not None:
                  v_[v_<vmin] = NaN
            if vmax is not None:
                  v_[v_>vmax] = NaN
                  
            gca().set_axis_bgcolor('black')
            
            if Log:
                  imshow(v_,origin='lower',extent=ext,aspect=aspect,
                         norm=LogNorm(vmin=vmin,vmax=vmax))
            else:
                  imshow(v_,origin='lower',extent=ext,aspect=aspect,vmin=vmin,vmax=vmax)

            # Tight colorbar
            # --------------
            _colorbar(tweak=tweak,ticks=ticks,format=format)

            # Labels
            # ------
            xlabel('Time (Hours UTC)')
            ylabel('Height (km)')
            if tit != None: 
                  title(tit)

def _colorbar(tit=None,tweak=0.16,**kwopts):                                                                
    """ Draw a colorbar """                                                     
                                                                                
    ax = gca()
    bbox = ax.get_position()                                                              
    l,b,w,h = bbox.bounds
    # dh = aspect * (h / w)
    dh = tweak * h
    cax = axes([l+w+0.01, b+dh/2, 0.04, h-dh]) # setup colorbar axes.
    colorbar(cax=cax,**kwopts)
    if tit is not None:
        title(tit)                                                           
    axes(ax)  # make the original axes current again
    
#....................................................................

if __name__ == "__main__":

    asm_Nv = 'http://opendap.nccs.nasa.gov:9090/dods/GEOS-5/fp/0.25_deg/assim/inst3_3d_asm_Nv'
    aer_Nv = 'http://opendap.nccs.nasa.gov:9090/dods/GEOS-5/fp/0.25_deg/assim/inst3_3d_aer_Nv'
    
    print("Loading CPL:")
    c = CPL('/Users/adasilva/data/CPL/CPL_ATB_19aug13.h5')

    # d.simulLidar(asm_Nv,aer_Nv)
    
    figure(figsize=(11,6))
        
    # d.curtain(1000*d.bsc_532[:,:],vmin=0,vmax=1)
    d.curtain(1000*abs(d.bsc_532[:,:]),vmin=0.01,vmax=10,Log=True,lower=True)

    show()
    

    g.simul('e572_fp.inst3_3d_asm_Nv.%y4%m2%d2_%h200z.nc4',
            'e572_fp.inst3_3d_aer_Nv.%y4%m2%d2_%h200z.nc4',
            'e572_fp.inst3_3d_ext532_Nv.%y4%m2%d2_%h200z.nc4',
            'e572_fp.inst3_3d_ext1064_Nv.%y4%m2%d2_%h200z.nc4' )

    g.simul('e572_fp.inst3_3d_asm_Nv.20110705_1800z.nc4',
            'e572_fp.inst3_3d_aer_Nv.20110705_1800z.nc4',
            'e572_fp.inst3_3d_ext532_Nv.20110705_1800z.nc4',
            'e572_fp.inst3_3d_ext1064_Nv.20110705_1800z.nc4' )

    g._attachVarT('e572_fp.inst3_3d_asm_Nv.%y4%m2%d2_%h200z.nc4',
                  ('H', 'RH', 'T',) )

    g.save()
    
