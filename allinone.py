import bs4 as bs
import urllib.request
from torrequest import TorRequest
from fake_useragent import UserAgent
from datetime import datetime
from geopy.geocoders import Bing
import folium
from tqdm import tqdm
from dataclasses import dataclass
from lxml import html
from itertools import groupby
from statistics import mean

#preparing the logs
timestamp = datetime.now()
timestamp = timestamp.strftime("%Y%m%d%H%M%S")
log_path = 'logs/log_{timestamp}.txt'.format(timestamp=timestamp)
log_path_flat_obj = 'logs/flats_{timestamp}.txt'.format(timestamp=timestamp)
with open(log_path, 'w') as f:
        f.write("\n")

#geolocator setup
geolocator = Bing(api_key="AvBAPo5JOlFEEXybd-kmWdAsiQD4zVnCZUpxHMFcXuj-4e0Nm854mI7WVHG5Qopp")

#set up user agent to randomize headers
ua = UserAgent()

#functions for __post__init__ of flat dataclass

def getLatAndLongt(street, distAndIndex):
    try:
        if len(street) < 1:
            return (None, None)
    except Exception as e:
        pass
    try:
        location = geolocator.geocode(street + " " + distAndIndex)
        return location.latitude, location.longitude
    except Exception as e:
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

#dataclass for the flats

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

# Scraping Links from immobilienscout24

source = urllib.request.urlopen('https://www.immobilienscout24.de/Suche/S-T/P-1/Wohnung-Miete/Hamburg/Hamburg').read()
soup = bs.BeautifulSoup(source, 'lxml')

# finding the number of pages as int
for option in soup.find_all('option'):
    ims_pages = option.get_text()
ims_pages = int(ims_pages)

#empty list for all flat links
linklist = []

#scraping links from each page on immobilienscout

print("\nScraping flats from immoscout\n")

for num_page in tqdm(range(1, ims_pages + 1)):
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
#using tor for anonimous requests

header = {'User-Agent':str(ua.random)}
tr = TorRequest(password='12345qwert!')
tr.reset_identity()  # Reset Tor
source = tr.get('https://www.wg-gesucht.de/wohnungen-in-Hamburg.55.2.1.0.html?category=2&city_id=55&rent_type=2&noDeact=1&img=1', headers=header).text
soup_wggesucht = bs.BeautifulSoup(source, 'lxml')

# Scraping the number of pages

for option in soup_wggesucht.find_all("a", {"class": "a-pagination"}):
    wg_pages = option.get_text()
wg_pages = int(wg_pages)

#scraping links from each page 

for i in tqdm(range(1, wg_pages+1)):

    with open(log_path, 'a') as f:
        f.write("Scraping Page {page} from wg-gesucht.de\n".format(page=i))
    
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

#empty list for flat objects

flatList = []

#scraping flat info

print("\nScraping flat information from items in the linkList\n")

#functions for scraping

def getTitle(soup):
    return soup.title.get_text()

def getStringFromSoup(soup, element, cssClass):
    try:
        return soup.find(element, {"class": cssClass}).get_text()
    except:
        return None

def getStringFromPath(tree, path):
    try:
        return tree.xpath(path)[0].text_content()
    except:
        return None

with open(log_path_flat_obj, 'w') as f:
    f.write("\n")

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

        header = {'User-Agent':str(ua.random)}
        tr = TorRequest(password='12345qwert!')
        tr.reset_identity()  # Reset Tor
        source = tr.get(link, headers=header)
        tree = html.fromstring(source.content)
    
        #check if the flat is deactivated
        """ todo: fix this shit later
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

        #checking content in [@id="main_column"] and setting variable for adjusting the divs in xpath

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
                f.write("Skipping " + link + " because xpath is broken\n")
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

    with open(log_path_flat_obj, 'a') as f:
        f.write(str(flatInfo) + "\n")
        f.write(str(flatInfo.lat) + "\n")
        f.write(str(flatInfo.longt) + "\n")
        f.write("\n")

#changes the color of the icon
def colorpicker(flat, priceDict):

    if flat.price > priceDict[flat.rooms] * 1.2:
        return "red"
    if flat.price < priceDict[flat.rooms] * 0.8:
        return 'green'
    else:
        return 'gray'

#calculate mean price for flats grouped by room number

def getRoomNumber(flat):
    return flat.rooms

meanPricePerRoom = {}

print(len(flatList))

flatList.sort(key=getRoomNumber)

for key, group in groupby(flatList, lambda x: x.rooms):
    meanRooms = mean([x.price for x in group])
    meanPricePerRoom[key] = meanRooms

print(meanPricePerRoom)

#building a map

map = folium.Map(location=[53.57532,10.01534], zoom_start = 12)

for flat in flatList:

    popuptext = "<b>" + flat.title + "</b></br>"\
        + str(flat.price) + " € (avg. " + str(meanPricePerRoom[flat.rooms]) + " €) </br>"\
            + str(flat.rooms) + " Zimmer, " + str(flat.sqm) + " m²</br>" + '<a href="{url}" target="_blank">'.format(url = flat.fullLink) + flat.fullLink + "</a>"

    if flat.longt == None:
        print("coordinates missing. skipping the marker.")
        continue

    folium.Marker([flat.lat, flat.longt], popup=popuptext, icon=folium.Icon(color=colorpicker(flat, meanPricePerRoom))).add_to(map)

map.save("map1.html")
