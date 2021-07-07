import matplotlib
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from mpl_toolkits.axes_grid1 import make_axes_locatable

import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import cartopy.feature as cfeature
import requests
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

'''A class for reading the UKMET text files generated at
http://tgftp.nws.noaa.gov/data/raw/wt/wtnt82.egrr..txt
and plotting information about storms in them'''


class UKMETReader:

    def __init__(self):
        '''Initialize text of latest UKMET text output'''
        
        self.text = self.fetch('http://tgftp.nws.noaa.gov/data/raw/wt/wtnt82.egrr..txt').text.split('\n')
        
    def fetch(self, url):
        '''Takes a URL and returns the file retrieved from that URL'''
        return requests.get(url)

    def parse_storms(self):
        '''Read through text and compile a dictionary of storm names with
        forecast time, lead time, position, pressure, and wind data'''

        def is_storm_data(first_word):
            '''Check if first_word is in the list of strings that begin
            storm info lines'''

            valid_strings = ['', 'ATCF', 'LEAD', 'VERIFYING',
                             '--------------', '1200UTC', '0000UTC']
            
            if any(first_word == valid for valid in valid_strings):
                return True
            return False

        def new_storm(line, num_new_storms):
            '''Find storm name in line, or create a name if the cyclone
            is forecast to develop. Then return initial values for the cyclone'''

            prefixes = ['TROPICAL', 'STORM', 'DEPRESSION', 'HURRICANE']

            #initialize new storm data structure
            cur_storm_dict = {
                'forecast_time' : [],
                'forecast_date' : [],
                'lead_time' : [],
                'lat' : [],
                'lon' : [],
                'pressure' : [],
                'wind' : []
            }
            
            for word in line:
                if not any(word == prefix for prefix in prefixes):
                    if word == 'NEW':
                        #create a name for forecast cyclone
                        return 'NEW_' + str(num_new_storms + 1), num_new_storms + 1, cur_storm_dict
                    else:
                        return word, num_new_storms, cur_storm_dict
            
        
        reading_storm = False
        storm = None
        num_new_storms = 0
        storms_dict = {}
        cur_storm_dict = {}
        
        #used to determine what storm variable is being looked at
        variable_keys ={
            0 : 'forecast_time',
            1 : 'forecast_date',
            2 : 'lead_time',
            3 : 'lat',
            4 : 'lon',
            5 : 'pressure',
            6 : 'wind'
        }
            
        for raw_line in self.text:
            #strip white space from current line
            line = raw_line.split()
            print(line)
            if len(line) == 0:
                continue
            elif reading_storm:
                #end reading_storm state if storm specific info is done
                '''format of file means one of the checked strings is always
                the beginning of a storm related line'''
                if is_storm_data(line[0]):
                    #would like to know ATCF ID
                    if line[0] == 'ATCF':
                        cur_storm_dict['id'] = line[3]
                    #mostly concerned with storm data point lines
                    elif 'UTC' in line[0]:
                        i = 0
                        while i < len(line):
                            #add current storm variable to cur_storm_dict
                            #avoid the post tropical label
                            if not ((i == 3 and (line[i] == 'POST-TROPICAL' or line[i] == 'CEASED')) or (i == 4 and (line[i] == 'TRACKING'))):
                                cur_storm_dict[variable_keys[i]].append(line[i])
                            elif line[i] == 'POST-TROPICAL':
                                cur_storm_dict[variable_keys[i-1]].pop()
                            i += 1
                            
                else:
                    storms_dict[storm] = cur_storm_dict
                    '''given that we were reading a storm, if the next line
                    is not related to a new storm then there is no useful info
                    left in the file'''
                    if line[0] == 'THIS':
                        break
                    if line[0] == 'FORECAST':
                        continue
                    else:
                        #new cyclone being read
                        #get name of cyclone if it exists, else make a new one
                        storm, num_new_storms, cur_storm_dict = new_storm(line, num_new_storms)
                        
            else:
                #initialize storm / storm reading mode if needed
                if any(line[0] == prefix for prefix in ['TROPICAL', 'STORM', 'DEPRESSION', 'HURRICANE']):
                    storm, num_new_storms, cur_storm_dict = new_storm(line, num_new_storms)
                    reading_storm = True 
        
        return storms_dict

    def plot(self, storms):
        '''plot map of storm track points and intensities'''

        #for differentiating between storms
        markers = ['o', 'v', 'D', '^', '<', 'H', '8',
                   's', 'p', '>', '*', 'h', 'd']
        
        fig = Figure(figsize = (12, 8))
        ax = fig.add_subplot(111, projection = ccrs.PlateCarree())
        ax.stock_img()
        gl = ax.gridlines(draw_labels = True)
        gl.xlocator = mticker.FixedLocator(range(-180, 180, 10))
        gl.ylocator = mticker.FixedLocator(range(-90, 90, 10))
        gl.xlabels_top = False
        gl.ylabels_right = False
        ax.coastlines()

        shpfilename = shpreader.natural_earth(resolution = '110m', category = 'cultural', name='admin_0_countries')
        cmap = plt.get_cmap('gist_ncar_r', 18)

        i = -1
        for storm in storms:
            i += 1

            #get rid of N's and W's in lats and lons, and convert strings to floats
            #ignoring possiblity of S's and E's under the bad assumption that a tropical 
            #cyclone in the EPAC or NATL would never fulfill those conditions
            storms[storm]['lon'] = [0 - float(lon[:-1]) for lon in storms[storm]['lon']]
            storms[storm]['lat'] = [float(lat[:-1]) for lat in storms[storm]['lat']]
            storms[storm]['pressure'] = [float(p) for p in storms[storm]['pressure']]
            times = [int(time) for time in storms[storm]['lead_time']]
            min_time = min(times)
            max_time = max(times)
            label = storm + ': Hour ' + str(min_time) + '-' + str(max_time)
            print('pressure: ' + str(storms[storm]['pressure']))
            print('lons: ' + str(storms[storm]['lon']))
            print('lats: ' + str(storms[storm]['lat']))
            ax.plot(storms[storm]['lon'], storms[storm]['lat'],
                    c = 'black', transform = ccrs.PlateCarree(), zorder = 1)
            ax.scatter(storms[storm]['lon'], storms[storm]['lat'],
                       c = storms[storm]['pressure'], cmap = cmap,
                       vmin = 930, vmax = 1020, label = label, s = 150,
                       marker = markers[i], transform = ccrs.PlateCarree(), zorder = 2)
        
        #set plot extent based on storm points
        #this probably doesn't handle the dateline or prime meridian well
        lons = [lon for storm in storms for lon in storms[storm]['lon']]
        lats = [lat for storm in storms for lat in storms[storm]['lat']]
        ax.set_extent([np.min(lons)-5, np.max(lons)+5, np.min(lats)-5, np.max(lats)+5])

        ax.legend(fontsize = 12, framealpha = 0.25, loc = 'upper right')
        leg = ax.get_legend()
        for handle in leg.legendHandles:
            handle.set_color('black')

        sm = plt.cm.ScalarMappable(cmap = cmap, norm = plt.Normalize(930, 1020))
        sm._A = []
        cbar = plt.colorbar(sm, ax = ax, orientation = 'vertical', pad = 0.00,
                            use_gridspec = True)

        labels = np.arange(930, 1020, 5)
        loc = labels
        cbar.set_ticks(loc)
        cbar.set_ticklabels(labels)
        cbar.set_label('Minimum Central Pressure (mb)')
        ax.add_feature(cfeature.NaturalEarthFeature(
            'cultural', 'admin_1_states_provinces_lines', '10m',
            edgecolor='gray', facecolor='gray'))
        ax.set_aspect('auto')

        #manually set extent. This should probably be changed to something else
        ax.set_title('UKMET TC Guidance ' +
                     ' '.join(self.text[4].split()[4:6]), size = 15, loc = 'center')

        #plt.tight_layout()
        #plt.show()
        pdf = PdfPages('UKMET.pdf')
        pdf.savefig(fig)
        pdf.close()
        
    def main(self):
        storms = self.parse_storms()
        for storm in storms:
            print(storm)
            for var in storms[storm]:
                print(var, ' : ', storms[storm][var])
        self.plot(storms)

if __name__ == "__main__":
    reader = UKMETReader()
    reader.main()
                        
                        
