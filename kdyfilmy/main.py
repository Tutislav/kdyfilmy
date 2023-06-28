import asyncio
from http.cookies import SimpleCookie
from json import dumps, loads

from js import document
from pyscript import Element
from sortedcontainers import SortedList

from movieapi import MovieAPI


COOKIES_MAX_AGE = 60 * 60 * 24 * 400
movieapi = MovieAPI()
movies = SortedList(key=lambda x:x["delta_days"])
search_results = []
search_running = False
input_query = Element("query").element
div_movies = Element("movies").element
div_search_results = Element("search-results").element
div_nomovies = Element("nomovies").element

async def search():
    global search_results, search_running
    if not search_running:
        search_running = True
        search_results = []
        div_search_results.innerHTML = ""
        query_text = input_query.value
        if input_query.value == query_text and len(query_text) > 3:
            search_results = await movieapi.search(query_text)
            for search_result in search_results:
                if any(search_result["url"] == movie["url"] for movie in movies):
                    search_results.remove(search_result)
                    continue
            search_results = search_results[0:4]
            for i, search_result in enumerate(search_results):
                search_result.update({"id": i})
                span_search_result = '''<span class="search-result" id="search-result''' + str(search_result["id"]) + '''">
                                        <span class="add-movie-button" onclick="pyscript.interpreter.globals.get(\'add_movie\')(\'''' + search_result["url"] + '''\', 1)">
                                            <i class="bi bi-plus-circle-dotted"></i><i class="bi bi-plus-circle-fill"></i>
                                        </span>
                                        <span class="name">''' + search_result["name"] + '''</span>
                                        <span class="year">''' + search_result["year"] + '''</span>
                                    </span>'''
                div_search_results.innerHTML = div_search_results.innerHTML + span_search_result
        search_running = False

async def toggle_countdown():
    toggle_countdown_button = Element("toggle-countdown-button").element
    countdown_icon_on = toggle_countdown_button.children[0]
    countdown_icon_off = toggle_countdown_button.children[1]
    countdown_shown = True
    if countdown_icon_on.className == "bi bi-5-square-fill visible":
        countdown_icon_on.className = "bi bi-5-square-fill hidden"
        countdown_icon_off.className = "bi bi-5-square visible"
        countdown_shown = False
    else:
        countdown_icon_on.className = "bi bi-5-square-fill visible"
        countdown_icon_off.className = "bi bi-5-square hidden"
        countdown_shown = True
    span_delta_days_list = document.querySelectorAll(".delta-days")
    for span in span_delta_days_list:
        if countdown_shown:
            span.className = span.className[0:-7]
        else:
            span.className += " hidden"

async def toggle_edit():
    toggle_edit_button = Element("toggle-edit-button").element
    edit_icon_on = toggle_edit_button.children[0]
    edit_icon_off = toggle_edit_button.children[1]
    edit_shown = False
    if edit_icon_on.className == "bi bi-wrench-adjustable-circle visible":
        edit_icon_on.className = "bi bi-wrench-adjustable-circle hidden"
        edit_icon_off.className = "bi bi-wrench-adjustable-circle-fill visible"
        edit_shown = True
    else:
        edit_icon_on.className = "bi bi-wrench-adjustable-circle visible"
        edit_icon_off.className = "bi bi-wrench-adjustable-circle-fill hidden"
        edit_shown = False
    span_edit_button_list = document.querySelectorAll(".delete-movie-button")
    for span in span_edit_button_list:
        if edit_shown:
            span.className = span.className[0:-7]
        else:
            span.className += " hidden"

async def add_movie(q: str, focus: bool = False):
    movie_dict = await movieapi.get(q)
    movie_dict.update({"id": len(movies)})
    if not any(movie_dict["name"] == movie["name"] for movie in movies):
        date_class = "released" if movie_dict["cinema_released"] else "unreleased"
        delta_days = ""
        if movie_dict["delta_days"] > 0 and movie_dict["delta_days"] < 9999:
            delta_class = "delta-days"
            if movie_dict["delta_days"] > 99:
                delta_class += " delta-days3"
            elif movie_dict["delta_days"] > 9:
                delta_class += " delta-days2"
            delta_days = '<span class="' + delta_class + '">' + str(movie_dict["delta_days"]) + "</span>"
        span_movie = '''<span class="movie" id="movie''' + str(movie_dict['id']) + '''" tabindex="0">
                    <span class="links">
                        <a class="csfd" target="_blank" href="''' + str(movie_dict['url']) + '''" tabindex="-1">
                            <span title="ČSFD.cz">''' + str(movie_dict['rating']) + '''<img src="https://static.pmgstatic.com/assets/images/39d04896278fe3eb71998df70adadd40/logo/csfd-logo.svg"></span>
                        </a>
                        <a class="imdb hidden" target="_blank" href="" tabindex="-1">
                            <span title="IMDb"><img src="https://m.media-amazon.com/images/G/01/IMDb/brand/guidelines/imdb/IMDb_Logo_Rectangle_Gold._CB443386186_.png"></span>
                        </a>
                        <a class="dabingforum hidden" target="_blank" href="" tabindex="-1">
                            <span title="Dabingforum.cz"><img src="https://www.dabingforum.cz/styles/prosilver/theme/images/site_logo_star.png"></span>
                        </a>
                        <span class="delete-movie-button hidden" title="Smazat" onclick="pyscript.interpreter.globals.get(\'delete_movie\')(\'''' + str(movie_dict['id']) + '''\')">
                            <i class="bi bi-trash"></i><i class="bi bi-trash-fill"></i>
                        </span>
                    </span>
                    <span class="poster">''' + delta_days + '''<img src="''' + movie_dict['poster'] + '''"></span>
                    <span class="name" title="''' + movie_dict["name"] + '''">''' + movie_dict["name"] + '''</span>
                    <span><span class="type">V kině: </span><b class="''' + date_class + '''">''' + movie_dict["cinema_date"] + '''</b></span><br>
                    <span id="digital_date''' + str(movie_dict['id']) + '''"><span class="type">Digital: </span><b>...</b></span><br>
                    <span id="dvd_date''' + str(movie_dict['id']) + '''"><span class="type">DVD: </span><b>...</b></span>
                </span>'''
        index = movies.bisect(movie_dict)
        if len(movies) > index:
            movie_prev = Element("movie" + str(movies[index]["id"])).element
            movie_prev.insertAdjacentHTML("beforebegin", span_movie)
        else:
            div_movies.innerHTML = div_movies.innerHTML + span_movie
        movies.add(movie_dict)
        await asyncio.sleep(0.5)
        span_movie = document.getElementById("movie" + str(movie_dict['id']))
        span_movie.style.opacity = 1
        if focus:
            span_movie.focus()
        await hide_spinner()
        div_nomovies.className = "hidden"
        await get_details(movie_dict)
        await save_cookies()

async def delete_movie(id: int):
    span_movie = document.getElementById("movie" + str(id))
    span_movie.remove()
    for movie in movies:
        if str(movie["id"]) == str(id):
            movies.discard(movie)
            break
    await save_cookies()
    if len(movies) == 0:
        div_nomovies.className = "visible"

async def get_details(movie_dict: dict):
    movie_dict = await movieapi.get_details(movie_dict)
    span_digital_date_value = Element("digital_date" + str(movie_dict['id']) + " b").element
    span_dvd_date_value = Element("dvd_date" + str(movie_dict['id']) + " b").element
    span_digital_date_value.innerHTML = movie_dict["digital_date"]
    span_dvd_date_value.innerHTML = movie_dict["dvd_date"]
    if (movie_dict["digital_released"]):
        span_digital_date_value.classList.add("released")
    else:
         span_digital_date_value.classList.add("unreleased")
    if (movie_dict["dvd_released"]):
        span_dvd_date_value.classList.add("released")
    else:
         span_dvd_date_value.classList.add("unreleased")
    span_movie = Element("movie" + str(movie_dict['id'])).element
    a_imdb = span_movie.children[0].children[1]
    a_imdb.href = movie_dict["imdb_url"]
    if movie_dict["imdb_url"] != "":
        a_imdb.children[0].innerHTML = movie_dict["imdb_rating"] + a_imdb.children[0].innerHTML
        a_imdb.className = "imdb visible"
    a_dabingforum = span_movie.children[0].children[2]
    a_dabingforum.href = movie_dict["dabing_url"]
    if movie_dict["dabing_url"] != "":
        a_dabingforum.className = "dabingforum visible"

async def hide_spinner():
    span_spinner = Element("spinner").element
    if span_spinner != None:
        span_spinner.remove()

async def load_cookies():
    cookies = SimpleCookie(document.cookie)
    if "data" in cookies:
        return loads(cookies["data"].value)
    else:
        return []

async def save_cookies():
    movies_cookie = []
    for movie in movies:
        movies_cookie.append(movie["url"])
    cookies = SimpleCookie()
    cookies["data"] = dumps(movies_cookie)
    cookies["data"].update({
        "max-age": COOKIES_MAX_AGE,
        "samesite": "Lax"
    })
    document.cookie = cookies["data"].OutputString()

async def main():
    saved_movies = await load_cookies()
    if len(saved_movies) == 0:
        await hide_spinner()
        div_nomovies.className = "visible"
    else:
        tasks = []
        for movie in saved_movies:
            tasks.append(asyncio.create_task(add_movie(movie)))
        await asyncio.gather(*tasks)
        await save_cookies()

asyncio.ensure_future(main())