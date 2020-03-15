import bs4 as bs
import urllib.request
from torrequest import TorRequest
from fake_useragent import UserAgent
from datetime import datetime
from geopy.geocoders import Bing
import folium
import pandas as pd
from tqdm import tqdm
from dataclasses import dataclass
from lxml import html

#preparing the logs
timestamp = datetime.now()
timestamp = timestamp.strftime("%Y%m%d%H%M%S")
log_path = 'logs/log_{timestamp}.txt'.format(timestamp=timestamp)
log_path_flat_obj = 'logs/flats_{timestamp}.txt'.format(timestamp=timestamp)
with open(log_path, 'w') as f:
        f.write("\n")


def getLatAndLongt(street, distAndIndex):
    try:
        if len(street) < 1:
            return (None, None)
    except Exception as e:
        print("No street provided: ", e)
    try:
        location = geolocator.geocode(street + " " + distAndIndex)
        return location.latitude, location.longitude
    except Exception as e:
        print("exception while locating an adress:", e)
        return (None, None)

def returnStringAsFloat(string):
    allowedDigits = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", ","]
    returnSting = ""
    for i in string:
        if i in allowedDigits:
            returnSting += i
    returnSting = returnSting.replace(",", ".")
    try:
        return float(returnSting)
    except:
        return None

@dataclass
class Flat:
  fullLink: str
  title: str
  price: str
  additionalCost: str
  rooms: str
  sqm: str
  street: str
  distAndIndex: str

  def __post_init__(self):
        self.lat, self.longt = getLatAndLongt(self.street, self.distAndIndex)
        self.price = returnStringAsFloat(self.price)
        self.additionalCost = returnStringAsFloat(self.additionalCost)
        self.rooms = returnStringAsFloat(self.rooms)
        self.sqm = returnStringAsFloat(self.sqm)



geolocator = Bing(api_key="AvBAPo5JOlFEEXybd-kmWdAsiQD4zVnCZUpxHMFcXuj-4e0Nm854mI7WVHG5Qopp")


# Scraping Links from immobilienscout24

source = urllib.request.urlopen('https://www.immobilienscout24.de/Suche/S-T/P-1/Wohnung-Miete/Hamburg/Hamburg').read()
soup = bs.BeautifulSoup(source, 'lxml')
# finding the number of pages as int
for option in soup.find_all('option'):
    pages = option.get_text()
pages = int(pages)

#scraping links from each page on immobilienscout

print("\nScraping flats from immoscout\n")

linklist = []

#for num_page in tqdm(range(1, pages + 1)):
for num_page in tqdm(range(1, 5)):
    with open(log_path, 'a') as f:
        f.write("Scraping Page {page} from immobilienscout24\n".format(page=num_page))
    source_immopage = urllib.request.urlopen(
        'https://www.immobilienscout24.de/Suche/S-T/P-{page}/Wohnung-Miete/Hamburg/Hamburg'.format(page=num_page)).read()
    soup = bs.BeautifulSoup(source_immopage, 'lxml')

    for url in soup.find_all('a', class_='result-list-entry__brand-title-container'):
        if len(url.get('href')) < 20:
            linklist.append(
                "https://www.immobilienscout24.de" + url.get('href'))
        else:
            with open(log_path, 'a') as f:
                f.write("Skipping " + url.get('href') + "\n")

print("\nScraping flats from wg_gesucht\n")

# Scraping Links from wg-gesucht.de

ua = UserAgent()
header = {'User-Agent':str(ua.random)}

tr = TorRequest(password='12345qwert!')
tr.reset_identity()  # Reset Tor
source = tr.get('https://www.wg-gesucht.de/wohnungen-in-Hamburg.55.2.1.0.html?category=2&city_id=55&rent_type=2&noDeact=1&img=1', headers=header).text

soup_wggesucht = bs.BeautifulSoup(source, 'lxml')

# Scraping the number of pages
for option in soup_wggesucht.find_all("a", {"class": "a-pagination"}):
    pages = option.get_text()
pages = int(pages)

#scraping links from the pages
for i in tqdm(range(0, pages+1)):
#for i in tqdm(range(0, 1)):

    with open(log_path, 'a') as f:
        f.write("Scraping Page {page} from wg-gesucht.de\n".format(page=i))
    
    ua = UserAgent()
    header = {'User-Agent':str(ua.random)}
    tr = TorRequest(password='12345qwert!')
    tr.reset_identity()
    source = tr.get("https://www.wg-gesucht.de/wohnungen-in-Hamburg.55.2.1.{num_page}.html?category=2&city_id=55&rent_type=2&noDeact=1&img=1".format(num_page=i), headers=header).text
    soup_wggesucht_pages = bs.BeautifulSoup(source, 'lxml')

    for url in soup_wggesucht_pages.find_all('a', class_='detailansicht'):
        if len(url.get('href')) < 60 and "https://www.wg-gesucht.de/" + url.get('href') not in linklist:
            linklist.append("https://www.wg-gesucht.de/" + url.get('href'))
        elif len(url.get('href')) < 60 and "https://www.wg-gesucht.de/" + url.get('href') in linklist:
            with open(log_path, 'a') as f:
                f.write("Skipping " + url.get('href') + " because it's a duplicate\n")
        else:
            with open(log_path, 'a') as f:
                f.write("Skipping " + url.get('href') + "\n")

#Summary

with open(log_path, 'a') as f:
    f.write("There are " + str(len(linklist)) + " links in the list\n\n")

#scraping flat info

FLATSSKIPPED = 0
FLATSERROR = 0
flats_nostreet_counter = 0
DEACTIVATED_FLATS = 0
flatList = []

with open(log_path, 'a') as f:
    f.write("Flats to scrape: " + str(len(linklist)) + "\n\n")

print("\nScraping the flat information \n")

def getTitle(soup):
    return soup.title.get_text()

def getStringFromSoup(soup, element, cssClass):
    try:
        return soup.find(element, {"class": cssClass}).get_text()
    except:
        print("exception while scraping " + element + "class: " + cssClass)
        return None

def getStringFromPath(tree, path):
    try:
        return tree.xpath(path)[0].text_content()
    except:
        print("exception while scraping " + path + "\ncontent of path: ")
        print(tree.xpath(path))
        return None



for link in tqdm(linklist):

    # scraping flat data from immobilienscout24

    if "immobilienscout24" in link:
        #continue
        try:
            source = urllib.request.urlopen(link).read()
        except Exception as e:
            with open(log_path, 'a') as f:
                f.write("Link was deactivated on immoscout:", e + "\n")
            continue

        soup = bs.BeautifulSoup(source, 'lxml')
        
        with open(log_path, 'a') as f:
            f.write("Scraping " + link + "\n")


        flatInfo = Flat(
            fullLink= link,
            title = getTitle(soup),
            price = getStringFromSoup(soup, "div", "is24qa-kaltmiete is24-value font-semibold is24-preis-value"),
            additionalCost = getStringFromSoup(soup, "dd", "is24qa-nebenkosten grid-item three-fifths"),
            rooms = getStringFromSoup(soup, "div", "is24qa-zi is24-value font-semibold"),
            sqm = getStringFromSoup(soup, "div", "is24qa-flaeche is24-value font-semibold"),
            street = getStringFromSoup(soup, "span", "block font-nowrap print-hide"),
            distAndIndex = getStringFromSoup(soup, "span", "zip-region-and-country")
            )

        flatList.append(flatInfo)

    # scraping flat data from wg-gesucht.de

    if "wg-gesucht.de" in link:

        # using tor to scrape anonymously
        ua = UserAgent()
        header = {'User-Agent':str(ua.random)}
        tr = TorRequest(password='12345qwert!')
        tr.reset_identity()  # Reset Tor
        source = tr.get(link, headers=header)
        tree = html.fromstring(source.content)

        #check if the flat is deactivated
        """ todo: fix ths shit later
        try:
            if getStringFromPath(tree, '//*[@id="main_column"]/div[2]/div/h4') == None:
                pass
            else:
                if "deaktiviert" in getStringFromPath(tree, '//*[@id="main_column"]/div[2]/div/h4'):
                    DEACTIVATED_FLATS += 1
                    with open(log_path, 'a') as f:
                        f.write("The flat is deactivated on wg_gesucht: " + link + "\n")
                    continue
        except Exception as e:
            print(e)"""

        with open(log_path, 'a') as f:
            f.write("Scraping " + link + "\n")
            f.write(str(len(tree.find_class('row'))) + '\n')

        #checking content in [@id="main_column"] and setting variable for adjusting the divs in xpath
        print(len(tree.find_class('row')))
        if len(tree.find_class('row')) >= 44:
            x = 0
        if len(tree.find_class('row')) == 43:
            x = 3
        if len(tree.find_class('row')) < 42:
            with open(log_path, 'a') as f:
                f.write("Skipping " + link + " because wg-gesucht blocked the request")
            continue

        #catching broken xpaths:
        try:
            street = tree.xpath('//*[@id="main_column"]/div[1]/div/div[{number}]/div[2]/a/text()[1]'.format(number = 11 - x))[0]
        except:
            with open(log_path, 'a') as f:
                f.write("Skipping " + link + " because xpath is broken")
            continue

        flatInfo = Flat(
            fullLink= link,
            title = tree.find(".//title").text,
            price = getStringFromPath(tree, '//*[@id="rent"]/label[1]'),
            additionalCost = getStringFromPath(tree, '//*[@id="utilities_costs"]/label[1]'),
            rooms = getStringFromPath(tree, '//*[@id="main_column"]/div[1]/div/div[{number}]/div[4]/h2'.format(number = 9 - x)),
            sqm = getStringFromPath(tree, '//*[@id="main_column"]/div[1]/div/div[{number}]/div[2]/h2'.format(number = 9 - x)),
            street = tree.xpath('//*[@id="main_column"]/div[1]/div/div[{number}]/div[2]/a/text()[1]'.format(number = 11 - x))[0],
            distAndIndex = tree.xpath('//*[@id="main_column"]/div[1]/div/div[{number}]/div[2]/a/text()[2]'.format(number = 11 - x))[0]
            )

        flatList.append(flatInfo)

with open(log_path_flat_obj, 'w') as f:
    for flat in flatList:
        f.write(flat)
        f.write("\n")

with open(log_path, 'a') as f:
    f.write("\n\n\n")
    f.write("Flats without a street: " + str(flats_nostreet_counter) + "\n")
    f.write("Skipped because there was an error: " + str(FLATSERROR) + "\n")
    f.write("Deactivated flats: " + str(DEACTIVATED_FLATS) + "\n")
    f.write("New list contains " + str(len(flatList)) + " flats\n")
    f.write("\n\n\n")

FLATSERROR = 0
MISSINGCORD = 0

#changes the color of the icon
def colorpicker(flat):

    if df.loc[flat[0]]["Price"] > mean_dist.loc[df.loc[flat[0]]["Rooms"]]["Price"]*1.2:
        return "red"
    if df.loc[flat[0]]["Price"] < mean_dist.loc[df.loc[flat[0]]["Rooms"]]["Price"]*0.8:
        return 'green'
    else:
        return 'gray'

#itterate to turn price and additional cost in float and sepatate district and index


for flat in flatList:

    if "immobilienscout24" in flat.fullLink:
        flat.distAndIndex = flat.distAndIndex.split(", ")
        for i in flat.distAndIndex:
            print(i)
        if len(flat.distAndIndex) < 2:
            flat.City = flat.distAndIndex[0].split(" ")[0]
            flat.District = flat.distAndIndex[0].split(" ")[1]
            continue
        else:
            flat.City = flat.distAndIndex[0]
            flat.District = flat.distAndIndex[1]
    #print(flat)
    if "wg-gesucht.de" in flat.fullLink:
        flat.distAndIndex = flat.distAndIndex.split(" ")
        print("wggesucht: " + flat.distAndIndex)
        flat.append(stringtoseparate[0] + " " + stringtoseparate[1])
        if len(stringtoseparate) > 2:
            flat.append(stringtoseparate[-2] + " " + stringtoseparate[-1])
            continue
        flat.append(stringtoseparate[2]) 

"""
save for later:
hasattr(foo, 'bar')
would return True if foo has an attribute named bar, otherwise False and
getattr(foo, 'bar', 'quux')
would return foo.bar if it exists, otherwise defaults to quux.
"""


df = pd.DataFrame(flat_list, columns =['Link', 'Name', 'Price', 'Additional costs', 'Rooms', 'Size', 'Street and Number', 'lat', 'long', 'City', 'District'])

mean_dist = df.groupby('Rooms') \
.agg({'Rooms':'size', 'Price':'mean'}) \
.rename(columns={'Rooms':'Rooms count','sent':'mean Price'})\
.reset_index()

decimals = 2    
mean_dist['Price'] = mean_dist['Price'].apply(lambda x: round(x, decimals))

df.set_index("Link", inplace=True)
mean_dist.set_index("Rooms", inplace=True)

map = folium.Map(location=[53.57532,10.01534], zoom_start = 12)

for flat in flat_list:

    try:
        popuptext = "<b>" + flat[1] + "</b></br>"\
         + str(flat[2]) + " € (avg. " + str(mean_dist.loc[df.loc[flat[0]]["District"]]["Price"]) + " €) </br>"\
          + flat[4] + " Zimmer, " + flat[5] + "</br>" + '<a href="{url}" target="_blank">'.format(url = flat[0]) + flat[0] + "</a>"
    except Exception as e:
        popuptext = "<b>" + flat[1] + "</b></br>"\
         + str(flat[2]) + " €</br>"\
          + flat[4] + " Zimmer, " + flat[5] + "</br>" + '<a href="{url}" target="_blank">'.format(url = flat[0]) + flat[0] + "</a>"
        print("general exception while creating a popup: ", e)

    try:

        if len(str(flat[-2])) < 1:
            print("coordinates missing. skipping the marker.")
            MISSINGCORD += 1
            continue
        folium.Marker([flat[-4], flat[-3]], popup=popuptext, icon=folium.Icon(color=colorpicker(flat))).add_to(map)

    except Exception as e:
        FLATSERROR += 1
        print("general exception while placing a marker:", e)

with open(log_path, 'a') as f:
    f.write("\n\n\n")
    f.write("Failed to place " + str(FLATSERROR) + " from " + str(len(flat_list)) + " flats on the map\n")
    f.write("Flats with missing cords: " + str(MISSINGCORD))

map.save("map1.html")
