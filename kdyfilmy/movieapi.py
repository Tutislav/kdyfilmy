import re
from datetime import datetime
from os import environ
from urllib import parse

from bs4 import BeautifulSoup


class MovieAPI():
    def __init__(self):
        self.csfd = CSFD()
        self.dvdsreleasedates = DVDsReleaseDates()
        self.dabingforum = Dabingforum()
    
    async def get(self, q: str):
        if "https://www.csfd.cz" in q:
            movie_dict = await self.csfd.parse_movie(q)
        else:
            movie_dict = await self.csfd.get_first(q)
        return movie_dict
    
    async def search(self, q: str):
        results = await self.csfd.search(q)
        return results

    async def get_details(self, movie_dict: dict):
        data_dvd = await self.dvdsreleasedates.search(movie_dict)
        movie_dict.update(data_dvd)
        data_dabing = await self.dabingforum.get(movie_dict)
        movie_dict.update(data_dabing)
        return movie_dict

    async def get_movies_names(self, genre: str = "", year: int = -1):
        if year == -1:
            year = datetime.strftime(datetime.now(), "%Y")
        url = "https://movieweb.com/movies/" + year + "/" + genre
        data = await get_data(url)
        soup = BeautifulSoup(data, "lxml")
        movies_links = soup.select("div.database-card-title a")
        movies_names = []
        for movie in movies_links:
            movie_date = movie.parent.parent.select_one("div.database-card-spec").text
            if movie_date != year:
                movies_names.append(movie.text + year)
        return movies_names

class CSFD():
    async def get_first(self, q: str):
        results = await self.search(q)
        return await self.parse_movie(results[0]["url"])

    async def search(self, q: str, movie_limit: int = 4, season_limit: int = 4):
        results = []
        for word in ["serie", "série", "sezón", "season"]:
            if word in q.lower():
                end_index = q.lower().find(word) - 1
                q = q[0:end_index]
                season_limit = season_limit + movie_limit
                movie_limit = 0
        if movie_limit > 0:
            movies = await self.search_movie(q)
            results.extend(movies[0:movie_limit])
        if season_limit > 0:
            seasons = await self.search_season(q)
            results.extend(seasons[0:season_limit])
        return results

    async def search_movie(self, q: str):
        q = parse.quote_plus(q)
        url = "https://www.csfd.cz/hledat/?series=0&creators=0&users=0&q={q}"
        data = await get_data(url.format(q=q))
        soup = BeautifulSoup(data, "lxml")
        results_raw = soup.select("a.film-title-name")
        results = []
        for result in results_raw:
            results.append({
                "name": result.text,
                "year": result.parent.select_one("span.info").text,
                "item_type": "movie",
                "url": "https://www.csfd.cz" + result.attrs["href"] + "prehled"
            })
        return results
    
    async def search_season(self, q: str):
        q = parse.quote_plus(q)
        url = "https://www.csfd.cz/hledat/?films=0&creators=0&users=0&q={q}"
        data = await get_data(url.format(q=q))
        soup = BeautifulSoup(data, "lxml")
        results_raw = soup.select("a.film-title-name")
        results = []
        for result in results_raw:
            span_info = result.parent.select("span.info")
            year = span_info[0].text
            if len(span_info) > 1:
                item_type = span_info[1].text.lstrip().rstrip()
                if item_type != "(série)":
                    continue
            results.append({
                "name": result.text,
                "year": year,
                "item_type": "season",
                "url": "https://www.csfd.cz" + result.attrs["href"] + "prehled"
            })
        return results
        
    async def parse_movie(self, url: str):
        data = await get_data(url)
        soup = BeautifulSoup(data, "lxml")
        name = soup.select_one("div.film-header-name h1").text.lstrip().rstrip()
        name_eng = soup.find("img", {"title": "USA"})
        item_type = soup.select_one("div.film-header-name span.type")
        if item_type != None:
            item_type = item_type.text.lstrip().rstrip()
            if item_type == "(série)":
                item_type = "season"
        else:
            item_type = "movie"
        year = soup.select_one("div.film-info-content div.origin span")
        if year != None:
            year = year.text.lstrip().rstrip()
            if "," in year:
                year = year[0:year.find(",")]
            if "(" in year:
                year = year[year.find("(") + 1:year.find("–")]
        if name_eng != None and not "pracovní název" in name_eng.parent.text:
            name_eng = name_eng.parent.text.lstrip().rstrip()
            newline_index = name_eng.find("\n")
            if newline_index > 0:
                name_eng = name_eng[0:newline_index]
            if len(name_eng) == 0:
                name_eng = name
        else:
            name_eng = name
        if item_type == "season":
            series_url = soup.select_one("div.film-header-name h1 a").attrs["href"]
            series_url = "https://www.csfd.cz" + series_url
            data_series = await get_data(series_url)
            soup_series = BeautifulSoup(data_series, "lxml")
            name_eng = soup_series.find("img", {"title": "USA"})
            if name_eng != None and not "pracovní název" in name_eng.parent.text:
                name_eng = name_eng.parent.text.lstrip().rstrip()
                newline_index = name_eng.find("\n")
                if newline_index > 0:
                    name_eng = name_eng[0:newline_index]
                if len(name_eng) == 0:
                    name_eng = name
            else:
                name_eng = name
        poster = soup.select_one("div.film-posters img")
        if poster != None:
            poster = poster.attrs["src"]
        else:
            poster = ""
        rating = soup.select_one("div.film-rating-average").text.lstrip().rstrip()
        cinema_date = "?"
        cinema_released = False
        p_date_types = soup.select("section.box-premieres li p")
        digital_date = "?"
        digital_released = False
        tv_date = "?"
        tv_released = False
        delta_days = 9999
        if p_date_types != None and len(p_date_types) > 0:
            for p_date_type in p_date_types:
                date = p_date_type.parent.select("span")[1].text.lstrip().rstrip()
                newline_index = date.find("\n")
                if newline_index > 0:
                    date = date[0:newline_index]
                country = p_date_type.parent.select_one("img")
                if country != None:
                    country = country.attrs["alt"]
                else:
                    country = "Worldwide"
                if "V kinech od" in p_date_type.text and "Česko" in country:
                    cinema_date = date
                    cinema_released = True if datetime.now() >= datetime.strptime(date, "%d.%m.%Y") else False
                    delta_days = (datetime.strptime(date, "%d.%m.%Y") - datetime.now()).days
                elif "VOD" in p_date_type.text:
                    digital_date = date
                    digital_released = True if datetime.now() >= datetime.strptime(date, "%d.%m.%Y") else False
                    delta_days = (datetime.strptime(date, "%d.%m.%Y") - datetime.now()).days
                elif "TV" in p_date_type.text:
                    tv_date = date
                    tv_released = True if datetime.now() >= datetime.strptime(date, "%d.%m.%Y") else False
                    delta_days = (datetime.strptime(date, "%d.%m.%Y") - datetime.now()).days
        else:
            date = "30.12." + year
            if item_type == "movie":
                cinema_date = year
                cinema_released = True if datetime.now() >= datetime.strptime(date, "%d.%m.%Y") else False
            else:
                tv_date = year
                tv_released = True if datetime.now() >= datetime.strptime(date, "%d.%m.%Y") else False
            delta_days = (datetime.strptime(date, "%d.%m.%Y") - datetime.now()).days
        result = {
            "name": name,
            "name_eng": name_eng,
            "poster": poster,
            "rating": rating,
            "cinema_date": cinema_date,
            "cinema_released": cinema_released,
            "digital_date": digital_date,
            "digital_released": digital_released,
            "tv_date": tv_date,
            "tv_released": tv_released,
            "delta_days": delta_days,
            "item_type": item_type,
            "url": url
        }
        return result

class DVDsReleaseDates():
    async def search(self, movie_dict: dict):
        q = parse.quote_plus(movie_dict["name_eng"])
        url = "https://www.dvdsreleasedates.com/search/?searchStr={q}"
        data = await get_data(url.format(q=q))
        soup = BeautifulSoup(data, "lxml")
        dates_released = soup.select("span.past.bold")
        dates_unreleased = soup.select("span.future.bold")
        date_estimated = soup.select_one("span.future")
        a_imdb = soup.select_one("span.imdblink.vam a")
        error = soup.select_one("td.medlargetext")
        dvds_rd_url = ""
        if error != None:
            error_text = error.text.lower()
            if "no results" in error_text and ":" in movie_dict["name_eng"]:
                movie_dict["name_eng"] = movie_dict["name_eng"].split(":")[0]
                return await self.search(movie_dict)
        else:
            dvds_rd_url = url.format(q=q)
        if a_imdb == None:
            a_imdb = soup.select_one("#movie > a")
        imdb_url = ""
        imdb_rating = ""
        if a_imdb != None:
            imdb_url = a_imdb.attrs["href"]
            imdb_rating = a_imdb.text if a_imdb.text != "NA" else "?"
        digital_released = False
        digital_date = "?"
        dvd_released = False
        dvd_date = "?"
        for date in dates_released:
            date_type = date.parent.find("b")
            if date_type != None and not "not announced" in date.text:
                if "Digital" in date_type.text and digital_date == "?":
                    digital_released = True
                    if not "est" in date.text:
                        try:
                            digital_date = datetime.strftime(datetime.strptime(date.text, "%B %d, %Y"), "%d.%m.%Y")
                        except:
                            digital_date = datetime.strftime(datetime.strptime(date.text, "%b %d, %Y"), "%d.%m.%Y")
                    else:
                        digital_date = datetime.strftime(datetime.strptime(date.text, "est %B %Y"), "cca %B %Y")
                elif "DVD" in date_type.text and dvd_date == "?":
                    dvd_released = True
                    if not "est" in date.text:
                        try:
                            dvd_date = datetime.strftime(datetime.strptime(date.text, "%B %d, %Y"), "%d.%m.%Y")
                        except:
                            dvd_date = datetime.strftime(datetime.strptime(date.text, "%b %d, %Y"), "%d.%m.%Y")
                    else:
                        dvd_date = datetime.strftime(datetime.strptime(date.text, "est %B %Y"), "cca %B %Y")
            if digital_date != "?" and dvd_date != "?":
                break
        for date in dates_unreleased:
            date_type = date.parent.find("b")
            if date_type != None and not "not announced" in date.text:
                if "Digital" in date_type.text and digital_date == "?":
                    digital_released = False
                    if not "est" in date.text:
                        try:
                            digital_date = datetime.strftime(datetime.strptime(date.text, "%B %d, %Y"), "%d.%m.%Y")
                        except:
                            digital_date = datetime.strftime(datetime.strptime(date.text, "%b %d, %Y"), "%d.%m.%Y")
                    else:
                        digital_date = datetime.strftime(datetime.strptime(date.text, "est %B %Y"), "cca %m.%Y")
                elif "DVD" in date_type.text and dvd_date == "?":
                    dvd_released = False
                    if not "est" in date.text:
                        try:
                            dvd_date = datetime.strftime(datetime.strptime(date.text, "%B %d, %Y"), "%d.%m.%Y")
                        except:
                            dvd_date = datetime.strftime(datetime.strptime(date.text, "%b %d, %Y"), "%d.%m.%Y")
                    else:
                        dvd_date = datetime.strftime(datetime.strptime(date.text, "est %B %Y"), "cca %m.%Y")
            if digital_date != "?" and dvd_date != "?":
                break
        if date_estimated != None and digital_date == "?":
            if "estimated" in date_estimated.text:
                digital_date = datetime.strftime(datetime.strptime(date_estimated.text, "is estimated for %B %Y"), "cca %m.%Y")
        dates = {
            "dvd_released": dvd_released,
            "dvd_date": dvd_date,
            "imdb_url": imdb_url,
            "imdb_rating": imdb_rating,
            "dvds_rd_url": dvds_rd_url
        }
        if digital_date != "?":
            dates.update({
            "digital_released": digital_released,
            "digital_date": digital_date
            })
        return dates

class Dabingforum():
    async def get(self, movie_dict: dict):
        name = movie_dict["name"]
        if movie_dict["item_type"] == "season":
            name = name[0:name.rfind(" - ")]
        q = parse.quote_plus(name)
        url = "https://dabingforum.cz/goto/film/{q}" 
        data = await get_data(url.format(q=q))
        dabing_url = ""
        if not "Litujeme, ale tohle tu nemáme" in data and movie_dict["item_type"] == "movie":
            dabing_url = url.format(q=q)
        else:
            results = await self.search(name, movie_dict["item_type"])
            for result in results:
                if re.search(name + " / " + movie_dict["name_eng"][0], result["name"]) or re.search(name + " / " + name[0], result["name"]):
                    dabing_url = result["url"]
                    break
        result = {
            "dabing_url": dabing_url
        }
        return result
    
    async def search(self, q: str, item_type: str):
        url = "https://www.dabingforum.cz/search.php?keywords={q}&sf=titleonly&sr=topics"
        if item_type == "movie":
            url += "&fid%5B%5D=3"
        else:
            url += "&fid%5B%5D=2"
        q = parse.quote_plus(q)
        data = await get_data(url.format(q=q))
        soup = BeautifulSoup(data, "lxml")
        results_raw = soup.select("a.topictitle")
        if len(results_raw) == 0:
            q = parse.quote_plus("intitle:") + q + parse.quote_plus(" host:dabingforum.cz")
            url = "https://search.seznam.cz/?q={q}"
            data = await get_data(url.format(q=q))
            soup = BeautifulSoup(data, "lxml")
            results_raw = soup.select("h3 a")
        results = []
        for result in results_raw:
            result_url = result.attrs["href"]
            if not "dabingforum.cz" in result_url:
                result_url = "https://www.dabingforum.cz/" + result.attrs["href"][2:len(result.attrs["href"])]
                result_url = result_url[0:result_url.find("&")]
            results.append({
                "name": result.text,
                "url": result_url
            })
        return results

async def get_data(url: str):
    PROXY = "https://cors.tutislav.workers.dev/"
    HEADERS = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"}
    if "HOME" in environ and environ["HOME"] == "/home/pyodide":
        from pyodide.http import pyfetch
        data_raw = await pyfetch(PROXY + url, method="GET", cache="force-cache", priority="high")
        data = await data_raw.string()
    else:
        from urllib import request
        with request.urlopen(request.Request(url, headers=HEADERS)) as urldata:
            data = urldata.read().decode()
    return data