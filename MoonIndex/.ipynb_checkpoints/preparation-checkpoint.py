import numpy as np
import pysptools.spectro as spectro
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import scipy as sp

###DATA PRETARION

def attach_wave (initial_cube,wavelengths):
    '''This function eliminates the first two empty bands, turn all anomalous values to nodata, and attach the wavelengths. 
    
    Inputs:
    initial_cube = M3 cube, 
    wavelengths = wavelengths file.
    
    Outputs:
    Prepared cube.'''

    #Removing bands
    initial_cube2=initial_cube[2:85,:,:]
    #Removing nodata
    initial_cube2.data[initial_cube2.data < -1000]= 0
    initial_cube2.data[initial_cube2.data > 1000]= 0
    #Attaching wavelength
    initial_cube2.coords['wavelength'] = ('band', wavelengths)
    cube_wave = initial_cube2.swap_dims({'band':'wavelength'})
    return cube_wave


def crop_cube (initial_cube,minnx,minny,maxxx,maxxy):
    '''Crop the prepared cube to a desired location, using the units of the coordinate system. Be caurefull to select values inside the coordinates of the image. 
    
    Inputs: 
    initial_cube = prepared cube, 
    minnx = lowest x lmiting value,
    minny = lowest y limiting value,
    maxxx = highest x limiting value, 
    maxxy = highest y limiting value.
    
    Outputs:
    Cropped cube.'''

    #Check input coordinates
    if minnx < initial_cube.coords['x'].min().data or minny < initial_cube.coords['y'].min().data or maxxx > initial_cube.coords['x'].max().data or maxxy > input_cube.coords['y'].max().data:
        raise ValueError("Invalid coordinate")
    #Assigning coordinates
    croped_cube=initial_cube.rio.clip_box(minx=minnx,miny=minny,maxx=maxxx,maxy=maxxy)
    #Creating the small rectangle
    rect_crop=patches.Rectangle((minnx,minny),(maxxx-minnx),(maxxy-minny),linewidth=1, edgecolor='r', facecolor='none')
    plot0, (axs, axs1)=plt.subplots(1,2, figsize=(5,20))
    #Plotting the cube
    initial_cube[0:3,:,:].plot.imshow(ax=axs,robust=True,add_labels=False)
    axs.add_patch(rect_crop)
    axs.set_aspect(1)
    axs.set_title('Full cube')
    #Plotting the cropped cube
    croped_cube[0:3,:,:].plot.imshow(ax=axs1,robust=True,add_labels=False)
    axs1.set_aspect(1)
    axs1.set_title('Cropped cube')
    plt.tight_layout() 
    return croped_cube

def crop_cube_size (initial_cube,cx1,cy1,cx2,cy2):
    '''Crop the prepared cube to a desired location, usign the number of lines and columns of the file. Be caurefull to select values inside the image size. 
    
    Inputs: 
    initial_cube = prepared cube, 
    cx1 = lowest x lmiting value,
    cy1 = highest x limiting value,
    cx2 = lowest y limiting value,
    cy2 = highest y limiting value.
    
    Outputs:
    Cropped cube.'''
    #Check input coordinates
    if cx1 < 0 or cy1 < 0 or cx2 > initial_cube.shape[2] or cy2 > input_cube.shape[1]:
        raise ValueError("Invalid coordinate")
    M3_cubecrop=initial_cube[:,cy1:cy2,cx1:cx2]
    rect_crop=patches.Rectangle((cx1,cy1),(cx2-cx1),(cy2-cy1),linewidth=1, edgecolor='r', facecolor='none')

    plot0, ax=plt.subplots(1,2, figsize=(5,20))
    ax[0].imshow(initial_cube[0,:,:])
    ax[0].set_title('Full cube')
    ax[0].add_patch(rect_crop)
    ax[1].imshow(M3_cubecrop[0,:,:])
    ax[1].set_title('Cropped cube')
    return M3_cubecrop

###CONTINUUM-REMOVAL

def midpoint(filtered_cube,wavelengths,peak_distance,peak_prominence):
    '''Finds the tie-point to limit the two absorption bands, used when the slope of the spectra is too steep. It used an automatic fucntion to detect local peaks. 
    
    Inputs:
    fitlered_cube = filtered cube,
    wavelengths = wavelengths,
    peak_distance = the minimum distance between peaks (6 is recommended),
    peak_prominence = the minimum prominence of the peaks (0.002 is recommended).
    
    Outputs:
    Tie-points cube.'''
    
    midpoint_cube=filtered_cube[0,:,:].copy()
    midpoint_stack=[]
    x_midpoint,y_midpoint,z_midpoint=filtered_cube.shape
    
    for a in range(filtered_cube.data.shape[1]):
        for b in range(filtered_cube.data.shape[2]):
            
            cube_filtered=filtered_cube[20:60,a,b]
            if cube_filtered[39] == 0: 
                midpoint_stack.append(0)
            else:
                #Selecting the range to find the peaks, it is the region between the 1 um and 2 um absorption bands
                midpoint_y=np.array(cube_filtered[0])
                midpoint_y2=np.append(midpoint_y,cube_filtered[39])
                midpoint_x=np.array(wavelengths[20])
                midpoint_x2=np.append(midpoint_x,wavelengths[59])
                midpoint_fit=np.polyfit(midpoint_x2,midpoint_y2,1)
                #Creating a linear fit in the desired range
                midpoint_polival=np.polyval(midpoint_fit,wavelengths[20:60])  
                #Diferrence between the data and the linear fit
                dif_cube=cube_filtered-midpoint_polival  
                #We use peak detection in the resulting curve to chose the value
                peaks, _ =sp.signal.find_peaks(dif_cube,distance=peak_distance, prominence=peak_prominence)  
                #If no peak is detected we select the arbitrary position of 1469.07 nm, obtained from literature (only a few percentage of pixels need this)
                if len(peaks) == 0:
                    midpoint_stack.append(wavelengths[42])  
                else:
                    midpoint_stack.append(wavelengths[peaks+20][-1])
    #Making the new cube
    midpoint_stacka=np.array(midpoint_stack)
    midpoint_stackb=midpoint_stacka.astype(np.float32)
    midpoint_cube.data=midpoint_stackb.reshape(y_midpoint,z_midpoint)
    return (midpoint_cube)


##Convex hull method
def convexhull_removal(filtered_cube, wavelengths_full,mid_point):
    '''Remove the continuum of the spectra using the convex-hull method. 
    
    Inputs:
    filtered_cube = fitlered cube, 
    wavelengths_full = wavelengths,
    mid_point = tie-point cube.
    
    Outputs:
    Continuum removed cube by convex hull(CH).'''

    #Copying the raster and cropping
    hull_cube=filtered_cube[0:74,:,:].copy()  
    wavelengths=wavelengths_full[0:74]
    stack_hull=[]  
    x_hull,y_hull,z_hull=hull_cube.shape
    
    for a in range(filtered_cube.data.shape[1]):
        for b in range(filtered_cube.data.shape[2]):
            
            input_filtered=filtered_cube.data[0:74,a,b]
            input_midpoint=mid_point.data[a,b]
            #Adding zeros to nodata pixels
            if input_filtered[39] == 0: 
                stack_hull.append(np.zeros(74))
            else:
                #Adding the tiepoint
                add_point=np.where(wavelengths==input_midpoint)[0]  
                add_array2=np.vstack((wavelengths[add_point],  input_filtered[add_point])).T
                #Doing the convex hull
                points = np.c_[wavelengths, input_filtered]  
                wavelengths, input_filtered = points.T
                augmented = np.concatenate([points, [(wavelengths[0], np.min(input_filtered)-1), (wavelengths[-1], np.min(input_filtered)-1)]], axis=0)
                hull = sp.spatial.ConvexHull(augmented)
                pre_continuum_points2 = points[np.sort([v for v in hull.vertices if v < len(points)])]
                pre_continuum_points2 = np.concatenate((pre_continuum_points2,add_array2), axis=0)
                pre_continuum_points2.sort(axis=0)
                continuum_points2=np.unique(pre_continuum_points2,axis=0)
                continuum_function2 = sp.interpolate.interp1d(*continuum_points2.T)
                filtered_cube_prime = input_filtered / continuum_function2(wavelengths)
                filtered_cube_prime[filtered_cube_prime >= 1]= 1
                filtered_cube_prime=np.nan_to_num(filtered_cube_prime)
            
                stack_hull.append(filtered_cube_prime)
    #Making the new cube        
    stack_hulla=np.array(stack_hull)
    stack_hullb=stack_hulla.astype(np.float32)
    hull_cube.data=stack_hullb.reshape(y_hull,z_hull,x_hull).transpose(2,0,1)
    return hull_cube


def find_minimums_ch (hull_cube,midpoint,wavelengths):
    '''This function finds the minimums around the 1 um and 2 um bands for the convex hull method. 
    
    Inputs:
    hull_cube = continuum-removed cube (CH),
    midpoint = tie-point,
    wavelengths = wavelegnths.
    
    Outputs:
    Minimum at 1 um and minimum at 2 um cubes.'''

    #Copying a cube from the original to maintain the projection
    min1000=hull_cube[0,:,:].copy()  
    stack_min1000=[]
    min2000=hull_cube[0,:,:].copy()
    stack_min2000=[]
    ymin1000,zmin1000=hull_cube[0,:,:].shape
    ymin2000,zmin2000=hull_cube[0,:,:].shape
    wavelengths=wavelengths[0:74]
    
    for a in range(hull_cube.data.shape[1]):
        for b in range(hull_cube.data.shape[2]):
        
            input_hull=hull_cube.data[:,a,b]
            #Adding zeros to nodata pixels
            if input_hull[39] == 0:
                
                stack_min1000.append(0)
                stack_min2000.append(0)
                
            else:
                #Finds the minimum value of the reflectance in wavelengths, the limtis is defined by the tie-point  
                input_midpoint=midpoint.data[a,b]
                pre_midpointp=np.where(wavelengths==input_midpoint)[0]
                midpointp=int(pre_midpointp)
                minimum_1000=np.argmin(input_hull[0:midpointp])  
                ofset=5
                #This creates a window around the minimum in the convex hull to do a posteriro fit
                fitxp=minimum_1000-ofset 
                #If the value is minor to 0, it converts it to 0
                fitxp=max(0,fitxp)  
                fitxp2=np.array(minimum_1000+ofset)
                #The -1 is to avoid that the resulting array is at the midpoint
                fitxp2[fitxp2 > midpointp]= midpointp-1  
                fitx=wavelengths[int(fitxp):int(fitxp2)]
                fity=input_hull[int(fitxp):int(fitxp2)]
                #Creates a second order fit aroud the minimum
                fit_1000=np.polyfit(fitx,fity,2)  
                polyval_1000=np.polyval(fit_1000,wavelengths[int(fitxp):int(fitxp2)])
                #Finds the minimum in the fit, this reduce the noise of the final data
                min1000p=np.where(polyval_1000== min(polyval_1000))[0]  
                final_1000=wavelengths[min1000p+fitxp]
                stack_min1000.append(final_1000[0])
                #This one does not need specific defintion of indexes vecause there is no risk of ocerlap with the midpoint
                minimum_2000=np.argmin(input_hull[midpointp:74])+midpointp  
                fit_2000=np.polyfit(wavelengths[int(minimum_2000-ofset):int(minimum_2000+ofset)],input_hull[int(minimum_2000-ofset):int(minimum_2000+ofset)],2)
                polyval_2000=np.polyval(fit_2000,wavelengths[int(minimum_2000-ofset):int(minimum_2000+ofset+1)])
                min2000p=np.where(polyval_2000== min(polyval_2000))[0]
                final_2000=wavelengths[min2000p+minimum_2000-ofset]
                stack_min2000.append(final_2000[0])
    #Making the new cubes
    stack_min1000a=np.array(stack_min1000)
    stack_min1000a[stack_min1000a ==  wavelengths[0]]= wavelengths[18]
    stack_min1000b=stack_min1000a.astype(np.float32)
    min1000.data=stack_min1000b.reshape(ymin1000,zmin1000
                                       
    stack_min2000a=np.array(stack_min2000)
    stack_min2000b=stack_min2000a.astype(np.float32)
    min2000.data=stack_min2000b.reshape(ymin2000,zmin2000)
    return (min1000,min2000)


def find_shoulders_ch (hull_cube,midpoint,min_1000,min_2000, wavelengths3):
    '''Find the shoulders around the minmums at 1 um and 2 um for the convex hull method. 
    
    Inputs:
    hull_cube = continuum removed cube (CH),
    midpoint = tie-point,
    min_1000 = the minimuum at 1 um cube, 
    min_2000 = the minimuum at 2 um cube,
    wavelengths3 = wavelegnths.
    
    Outputs:
    Left and right shoulders of the 1 um absorption band, left and right shoulder of the 2 um absorption band.'''

    #Copying a cube from the original to maintain the projection
    shoulder0=hull_cube[0,:,:].copy()
    stack_shoulder0=[]
    shoulder1=hull_cube[0,:,:].copy()
    stack_shoulder1=[]
    shoulder2=hull_cube[0,:,:].copy()
    stack_shoulder2=[]
    shoulder3=hull_cube[0,:,:].copy()
    stack_shoulder3=[]
    y5,z5=hull_cube[0,:,:].shape
    wavelengths=wavelengths3[0:74]

    for a in range(hull_cube.data.shape[1]):
        for b in range(hull_cube.data.shape[2]):

            input_hull_shoulder=hull_cube.data[:,a,b]
            #Adding zeros to nodata pixels
            if input_hull_shoulder[39] == 0:
                
                stack_shoulder0.append(0)
                stack_shoulder1.append(0)
                stack_shoulder2.append(0)
                stack_shoulder3.append(0)
            else:
                #Input of the minimums and tie-point
                input_midpoint_shoulder=midpoint.data[a,b]
                pre_midpointp=np.where(wavelengths==input_midpoint_shoulder)[0]
                midpoint_shoulderp=int(pre_midpointp)
                input_min1000=min_1000.data[a,b]
                pre_input_min1000p=np.where(wavelengths==input_min1000)[0]
                min1000p=int(pre_input_min1000p)
                input_min2000=min_2000.data[a,b]
                pre_input_min2000p=np.where(wavelengths==input_min2000)[0]
                min2000p=int(pre_input_min2000p)
                #Calculating the left shoulder of the 1 um absorption band. Works similar to the maximums, but the last argument ensures than only the last value is returned
                shoulder_0=np.where(input_hull_shoulder[0:min1000p] == max(input_hull_shoulder[0:min1000p]))[0][-1]  
                ofset=3
                #This creates a window around the maximum in the convex hull to do a posterior fit
                fitxp0=shoulder_0-ofset  
                #If the value is minor to 0, it converts it to 0
                fitxp0=max(0, fitxp0) 
                fitx0=wavelengths[int(fitxp0):int(shoulder_0+ofset)]
                fity0=input_hull_shoulder[int(fitxp0):int(shoulder_0+ofset)]
                #Creates a second order fit aroud the maximums
                fit_0=np.polyfit(fitx0,fity0,2)  
                polyval_0=np.polyval(fit_0,wavelengths[int(fitxp0):int(shoulder_0+ofset+1)])
                #Finds the minimum in the fit, this reduce the noise of the final data
                max0p=np.where(polyval_0== max(polyval_0))[0]  
                final_0=wavelengths[max0p+fitxp0]
                stack_shoulder0.append(final_0[0])
                #Calculating the right shoulder of the 1 um absorption band
                shoulder_1=np.where(input_hull_shoulder[min1000p:midpoint_shoulderp] == max(input_hull_shoulder[min1000p:midpoint_shoulderp]))[0][-1]+min1000p
                fitxp1=shoulder_1-ofset
                fitxp1=max(0,fitxp1)
                fit_1=np.polyfit(wavelengths[int(fitxp1):int(shoulder_1+ofset)],input_hull_shoulder[int(fitxp1):int(shoulder_1+ofset)],2)
                polyval_1=np.polyval(fit_1,wavelengths[int(fitxp1):int(shoulder_1+ofset+1)])
                max1p=np.where(polyval_1== max(polyval_1))[0]
                final_1=wavelengths[max1p+fitxp1]
                stack_shoulder1.append(final_1[0])
                #Calculating the left shoulder of the 2 um absorption band
                #To avoid errors where the aborsoption feature is weak, if the value is too low it assing the midpoint
                if midpoint_shoulderp-min2000p < 0:  
                
                    shoulder_2=np.where(input_hull_shoulder[midpoint_shoulderp:min2000p] == max(input_hull_shoulder[midpoint_shoulderp:min2000p]))[0][-1]+midpoint_shoulderp
                    value_2=wavelengths[shoulder_2]
                    stack_shoulder2.append(value_2)
                
                else:
                
                    stack_shoulder2.append(wavelengths[midpoint_shoulderp])
                #Calculating the right shoulder of the 2 um absorption band
                shoulder_3=np.where(input_hull_shoulder[min2000p:74] == max(input_hull_shoulder[min2000p:74]))[0][-1]+min2000p
                value_3=wavelengths[shoulder_3]
                stack_shoulder3.append(value_3)
    #Making the new cubes
    stack_shoulder0a=np.array(stack_shoulder0)
    stack_shoulder0b=stack_shoulder0a.astype(np.float32)
    shoulder0.data=stack_shoulder0b.reshape(y5,z5)

    stack_shoulder1a=np.array( stack_shoulder1)
    stack_shoulder1b=stack_shoulder1a.astype(np.float32)
    shoulder1.data=stack_shoulder1b.reshape(y5,z5)

    stack_shoulder2a=np.array(stack_shoulder2)
    stack_shoulder2b=stack_shoulder2a.astype(np.float32)
    shoulder2.data=stack_shoulder2b.reshape(y5,z5)

    stack_shoulder3a=np.array(stack_shoulder3)
    stack_shoulder3b=stack_shoulder3a.astype(np.float32)
    shoulder3.data=stack_shoulder3b.reshape(y5,z5)
    
    return (shoulder0, shoulder1, shoulder2, shoulder3)

##Linear fit method

def continuum_removal_lf (filtered_cube,wavelengths,order1,order2):
    '''Remove the continuum of the spectra using the linear-fit method. The limits for the fits are manually defined using values established in the literature.
    
    Inputs:
    filtered_cube = fitlered cube, 
    wavelengths = wavelengths,
    order1 = polynomial order for the first absoprtion band.
    order2 = polynomial order for the second absoprtion band.
        
    Outputs:
    Continuum removed cube by linear fit(LF).'''
    
    lf=filtered_cube[0:74,:,:].copy()
    stack_lf=[]
    x,y,z=lf[:,:,:].shape
    wavelengths=wavelengths[0:74]
    
    for a in range(filtered_cube.data.shape[1]):
        for b in range(filtered_cube.data.shape[2]):
            #Second order fit for 1000 nm, it used a range for the two shoudlers around the 1000 nm absorption
            lf_cube=filtered_cube.data[0:74,a,b]  
            
            if lf_cube[39] == 0: 
                stack_lf.append(np.zeros(74))
            else:
                #The limits of the fit are defined manually by values used in the literature
                fitx10001=wavelengths[1:7]
                fitx10002=wavelengths[39:42]
                fitx1000=np.hstack((fitx10001,fitx10002))
                fity10001=lf_cube[1:7]
                fity10002=lf_cube[39:42]
                fity1000=np.hstack((fity10001,fity10002))
                fit1000=np.polyfit(fitx1000,fity1000,order1)
                polival1000=np.polyval(fit1000,wavelengths[0:42])
                #Fit for 2000 nm, linear
                fitx2000=np.hstack((fitx10002,wavelengths[73])) 
                fity2000=np.hstack((fity10002,lf_cube[73]))
                fit2000=np.polyfit(fitx2000,fity2000,order2)
                polival2000=np.polyval(fit2000,wavelengths[42:74])
                #Continuum removal by dividing
                continuum=np.hstack((polival1000,polival2000))  
                continuum_removed=lf_cube/continuum
                continuum_removed[continuum_removed > 1]= 1
                stack_lf.append(continuum_removed)
            
    stack_lfa=np.array(stack_lf)
    lf.data=stack_lfa.reshape(y,z,x).transpose(2,0,1)
    
    return(lf)


def find_minimuumslf (lf_cube,wavelengths):
    '''This function finds the minimums around the 1 um and 2 um bands for the linear fit method. 
    
    Inputs:
    lf_cube = continuum-removed cube (LF),
    wavelengths = wavelegnths.
    
    Outputs:
    Minimum at 1 um and minimum at 2 um cubes.'''

    #Copied from the original to maintain the projection
    min_1000lf=lf_cube[0,:,:].copy()  
    stack_min_1000lf=[]
    min_2000lf=lf_cube[0,:,:].copy()
    stack_min_2000lf=[]
    y,z=lf_cube[0,:,:].shape

    for a in range(lf_cube.data.shape[1]):
        for b in range(lf_cube.data.shape[2]):
        
            min_lf=lf_cube.data[:,a,b]
            
            if min_lf[39] == 0:
                
                stack_min_1000lf.append(0)
                stack_min_2000lf.append(0)
                
            else:
                #Finds the minimum value of the reflectance in wavelengths, the limit is defined by the midpoint
                minimum_1000lf=np.argmin(min_lf[7:39])+7    
                ofsetlf=5
                #This creates a window around the minimum in the convex hull to do a posterior fit
                fitxplf=minimum_1000lf-ofsetlf  
                fitxp2lf=np.array(minimum_1000lf+ofsetlf)
                fitxp2lf[fitxp2lf > 39]= 38
                fitxlf=wavelengths[int(fitxplf):int(fitxp2lf)]
                fitylf=min_lf[int(fitxplf):int(fitxp2lf)]
                #Creates a second order fit around the 1 um minimum
                fit_1000lf=np.polyfit(fitxlf,fitylf,2)  
                polyval_1000lf=np.polyval(fit_1000lf,wavelengths[int(fitxplf):int(fitxp2lf)])
                #Finds the minimum in the fit, this reduces the noise of the final data
                min1000plf=np.argmin(polyval_1000lf)  
                final_1000lf=wavelengths[min1000plf+fitxplf]
                stack_min_1000lf.append(final_1000lf)
                #Find the minimum at 2 um
                minimum_2000lf=np.argmin(min_lf[39:74])+39
                min2000=minimum_2000lf+ofsetlf
                if min2000 > 73: min2000=73
                fit_2000lf=np.polyfit(wavelengths[int(minimum_2000lf-ofsetlf):int(min2000)],min_lf[int(minimum_2000lf-ofsetlf):int(min2000)],2)
                polyval_2000lf=np.polyval(fit_2000lf,wavelengths[int(minimum_2000lf-ofsetlf):int(minimum_2000lf+ofsetlf+1)])
                min2000plf=np.argmin(polyval_2000lf)
                wave_index2000=min2000plf+minimum_2000lf-ofsetlf
                #Limits the calculations to the values on the literature
                if wave_index2000 > 73: wave_index2000=73
                if wave_index2000 < 39: wave_index2000=39
                final_2000lf=wavelengths[wave_index2000]
                stack_min_2000lf.append(final_2000lf)
    
    
    stack_min1000lfa=np.array(stack_min_1000lf)
    stack_min1000lfa[stack_min1000lfa ==  wavelengths[0]]= wavelengths[18]
    min_1000lf.data=stack_min1000lfa.reshape(y,z)

    stack_min2000lfa=np.array(stack_min_2000lf)
    min_2000lf.data=stack_min2000lfa.reshape(y,z)
    return (min_1000lf,min_2000lf)

#Finding the shoulders with the lienar fit method

def find_shoulders_lf (lf_cube,min_1000lf,min_2000lf, wavelengths):
    '''Find the shoulders around the minmums at 1 um and 2 um for the linear fit method. 
    
    Inputs:
    lf_cube = continuum removed cube (lf),
    min_1000lf = the minimuum at 1 um cube, 
    min_2000lf = the minimuum at 2 um cube,
    wavelengths = wavelegnths.
    
    Outputs:
    Left and right shoulders of the 1 um absorption band, left and right shoulder of the 2 um absorption band (the rigth shoulder of the 1 um is the same as the left shoulder of the 2 um absorption band).'''
    
    shoulder0lf=lf_cube[0,:,:].copy()
    stack_shoulder0lf=[]
    shoulder1lf=lf_cube[0,:,:].copy()
    stack_shoulder1lf=[]
    shoulder2lf=lf_cube[0,:,:].copy()
    stack_shoulder2lf=[]
    y,z=lf_cube[0,:,:].shape

    for a in range(lf_cube.data.shape[1]):
        for b in range(lf_cube.data.shape[2]):

            input_shoulderlf=lf_cube.data[:,a,b]
            if input_shoulderlf[39] == 0:
                
                stack_shoulder0lf.append(0)
                stack_shoulder1lf.append(0)
                stack_shoulder2lf.append(0)
                
            else:
                input_min1000lf=min_1000lf.data[a,b]
                pre_input_min1000plf=np.where(wavelengths==input_min1000lf)[0]
                min1000plf=int(pre_input_min1000plf)
                input_min2000lf=min_2000lf.data[a,b]
                pre_input_min2000plf=np.where(wavelengths==input_min2000lf)[0]
                min2000plf=int(pre_input_min2000plf)
                 # The last argument ensures than only the last value is returned
                shoulder_0lf=np.where(input_shoulderlf[0:min1000plf] == max(input_shoulderlf[0:min1000plf]))[0][-1] 
                ofsetlf=3
                 #This creates a window around the maximum in the convex hull to do a posterior fit
                fitxp0lf=shoulder_0lf-ofsetlf 
                #If the value is minor to 0, it converts it to 0
                fitxp0lf=max(0, fitxp0lf) 
                fitx0lf=wavelengths[int(fitxp0lf):int(shoulder_0lf+ofsetlf)]
                fity0lf=input_shoulderlf[int(fitxp0lf):int(shoulder_0lf+ofsetlf)]
                #Creates a second order fit aroud the maximums
                fit_0lf=np.polyfit(fitx0lf,fity0lf,2)  
                polyval_0lf=np.polyval(fit_0lf,wavelengths[int(fitxp0lf):int(shoulder_0lf+ofsetlf+1)])
                #Finds the maximum in the fit, this reduce the noise of the final data
                max0plf=np.where(polyval_0lf== max(polyval_0lf))[0]  
                final_0lf=wavelengths[max0plf+fitxp0lf]
                stack_shoulder0lf.append(final_0lf[0])
                #Finds the right shoulder of the 1 um absorption band (same as the left shoulder of the 2 um absorption band)
                shoulder_1lf=np.where(input_shoulderlf[min1000plf:min2000plf+1] == max(input_shoulderlf[min1000plf:min2000plf+1]))[0][-1]+min1000plf
                maxs1=shoulder_1lf+ofsetlf
                if maxs1 > 74: maxs1=74
                fitxp1lf=shoulder_1lf-ofsetlf
                fitxp1lf=max(0,fitxp1lf)
                fit_1lf=np.polyfit(wavelengths[int(fitxp1lf):int(maxs1)],input_shoulderlf[int(fitxp1lf):int(maxs1)],2)
                polyval_1lf=np.polyval(fit_1lf,wavelengths[int(fitxp1lf):int(shoulder_1lf+ofsetlf+1)])
                max1plf=np.where(polyval_1lf== max(polyval_1lf))[0]
                final_1lf=wavelengths[max1plf+fitxp1lf]
                stack_shoulder1lf.append(final_1lf[0])
                #The right shoulder of the 2 um absorption band is the last band
                value_2=wavelengths[74]
                stack_shoulder2lf.append(value_2)

    stack_shoulder0lfa=np.array(stack_shoulder0lf)
    shoulder0lf.data=stack_shoulder0lfa.reshape(y,z)

    stack_shoulder1lfa=np.array( stack_shoulder1lf)
    shoulder1lf.data=stack_shoulder1lfa.reshape(y,z)

    stack_shoulder2lfa=np.array(stack_shoulder2lf)
    shoulder2lf.data=stack_shoulder2lfa.reshape(y,z)
    return (shoulder0lf, shoulder1lf, shoulder2lf)

