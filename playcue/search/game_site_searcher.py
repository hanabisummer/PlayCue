from __future__ import annotations

import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from playcue.models import LinkItem
from playcue.ui import i18n


class SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[tuple[str, str]] = []
        self._href = ""
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        if not href:
            return
        self._href = href
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._href:
            return
        title = " ".join("".join(self._text_parts).split())
        if title:
            self.results.append((title, self._href))
        self._href = ""
        self._text_parts = []


class GameSiteSearcher:
    SEARCH_URL = "https://duckduckgo.com/html/"
    QUERY_SUFFIXES = ("攻略", "wiki", "guide")
    EXCLUDED_DOMAINS = (
        "duckduckgo.com",
        "google.com",
        "bing.com",
        "yahoo.co.jp",
        "youtube.com",
        "youtu.be",
        "x.com",
        "twitter.com",
        "facebook.com",
        "instagram.com",
    )
    GUIDE_DOMAINS = (
        "game8.jp",
        "gamewith.jp",
        "altema.jp",
        "appmedia.jp",
        "kamigame.jp",
        "wikiwiki.jp",
        "w.atwiki.jp",
        "pcgamingwiki.com",
        "fandom.com",
    )
    INFO_DOMAINS = (
        "4gamer.net",
        "famitsu.com",
        "gamespark.jp",
        "automaton-media.com",
        "dengekionline.com",
        "gamer.ne.jp",
        "inside-games.jp",
        "ign.com",
        "gamespot.com",
    )
    HIGH_TRAFFIC_DOMAINS = (
        "store.steampowered.com",
        "steamcommunity.com",
        "playstation.com",
        "xbox.com",
        "nintendo.com",
        "reddit.com",
        "metacritic.com",
    )
    OFFICIAL_LINKS = {
        "ff14": {
            "ja": LinkItem("FINAL FANTASY XIV The Lodestone", "https://jp.finalfantasyxiv.com/lodestone/"),
            "en": LinkItem("FINAL FANTASY XIV The Lodestone", "https://na.finalfantasyxiv.com/lodestone/"),
        },
        "ffxiv": {
            "ja": LinkItem("FINAL FANTASY XIV The Lodestone", "https://jp.finalfantasyxiv.com/lodestone/"),
            "en": LinkItem("FINAL FANTASY XIV The Lodestone", "https://na.finalfantasyxiv.com/lodestone/"),
        },
        "finalfantasyxiv": {
            "ja": LinkItem("FINAL FANTASY XIV The Lodestone", "https://jp.finalfantasyxiv.com/lodestone/"),
            "en": LinkItem("FINAL FANTASY XIV The Lodestone", "https://na.finalfantasyxiv.com/lodestone/"),
        },
        "finalfantasy14": {
            "ja": LinkItem("FINAL FANTASY XIV The Lodestone", "https://jp.finalfantasyxiv.com/lodestone/"),
            "en": LinkItem("FINAL FANTASY XIV The Lodestone", "https://na.finalfantasyxiv.com/lodestone/"),
        },
    }

    @classmethod
    def search(cls, game_title: str, max_results: int = 5) -> tuple[LinkItem, ...]:
        collected: list[tuple[int, int, LinkItem]] = []
        seen: set[str] = set()
        seen_sites: set[str] = set()
        order = 0
        for link in cls._known_official_links(game_title):
            key = cls.normalized_url_key(link.url)
            site_key = cls.site_key(link.url)
            seen.add(key)
            seen_sites.add(site_key)
            collected.append((10000 + cls._language_score(link), order, link))
            order += 1
        for suffix in cls.QUERY_SUFFIXES:
            html = cls._fetch_html(f"{game_title} {suffix}")
            for title, href in cls._parse_html(html):
                link = cls._to_link(title, href)
                if link is None:
                    continue
                key = cls.normalized_url_key(link.url)
                if key in seen:
                    continue
                site_key = cls.site_key(link.url)
                if site_key in seen_sites:
                    continue
                seen.add(key)
                seen_sites.add(site_key)
                collected.append((cls._score(link), order, link))
                order += 1
        collected.sort(key=lambda item: (-item[0], item[1]))
        return tuple(item[2] for item in collected[:max_results])

    @classmethod
    def links_from_html(cls, html: str, max_results: int = 5) -> tuple[LinkItem, ...]:
        collected: list[tuple[int, int, LinkItem]] = []
        seen: set[str] = set()
        seen_sites: set[str] = set()
        for order, (title, href) in enumerate(cls._parse_html(html)):
            link = cls._to_link(title, href)
            if link is None:
                continue
            key = cls.normalized_url_key(link.url)
            if key in seen:
                continue
            site_key = cls.site_key(link.url)
            if site_key in seen_sites:
                continue
            seen.add(key)
            seen_sites.add(site_key)
            collected.append((cls._score(link), order, link))
        collected.sort(key=lambda item: (-item[0], item[1]))
        return tuple(item[2] for item in collected[:max_results])

    @classmethod
    def normalized_url_key(cls, url: str) -> str:
        parsed = urllib.parse.urlparse(url.strip())
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path.rstrip("/")
        return urllib.parse.urlunparse((parsed.scheme.lower(), netloc, path, "", parsed.query, ""))

    @staticmethod
    def site_key(url: str) -> str:
        netloc = urllib.parse.urlparse(url.strip()).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc

    @classmethod
    def _fetch_html(cls, query: str) -> str:
        params = urllib.parse.urlencode({"q": query})
        request = urllib.request.Request(
            f"{cls.SEARCH_URL}?{params}",
            headers={"User-Agent": "Mozilla/5.0 PlayCue"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.read().decode("utf-8", errors="replace")

    @staticmethod
    def _parse_html(html: str) -> list[tuple[str, str]]:
        parser = SearchResultParser()
        parser.feed(html)
        return parser.results

    @classmethod
    def _to_link(cls, title: str, href: str) -> LinkItem | None:
        url = cls._unwrap_url(href)
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        domain = parsed.netloc.lower()
        if any(domain == excluded or domain.endswith(f".{excluded}") for excluded in cls.EXCLUDED_DOMAINS):
            return None
        name = cls._clean_title(title)
        if not name:
            return None
        return LinkItem(name=name, url=urllib.parse.urlunparse(parsed._replace(fragment="")))

    @staticmethod
    def _unwrap_url(href: str) -> str:
        if href.startswith("//"):
            href = f"https:{href}"
        elif href.startswith("/"):
            href = f"https://duckduckgo.com{href}"
        parsed = urllib.parse.urlparse(href)
        if parsed.netloc.lower().endswith("duckduckgo.com"):
            query = urllib.parse.parse_qs(parsed.query)
            if query.get("uddg"):
                return query["uddg"][0]
        return href

    @staticmethod
    def _clean_title(title: str) -> str:
        title = re.sub(r"\s+", " ", title).strip()
        return title[:80]

    @classmethod
    def _score(cls, link: LinkItem) -> int:
        domain = cls.site_key(link.url)
        text = f"{link.name} {link.url}".lower()
        if cls._looks_official_forum(domain, text):
            score = 4000
        elif cls._looks_official_site(domain, text):
            score = 5000
        elif cls._domain_matches(domain, cls.GUIDE_DOMAINS):
            score = 3000
        elif cls._domain_matches(domain, cls.INFO_DOMAINS):
            score = 2000
        elif cls._domain_matches(domain, cls.HIGH_TRAFFIC_DOMAINS):
            score = 1000
        else:
            score = 0
        if any(keyword in text for keyword in ("攻略", "wiki", "guide", "walkthrough")):
            score += 100
        if any(keyword in text for keyword in ("official", "公式")):
            score += 50
        score += cls._language_score(link)
        return score

    @classmethod
    def _known_official_links(cls, game_title: str) -> tuple[LinkItem, ...]:
        key = re.sub(r"[^a-z0-9]+", "", game_title.lower())
        links = cls.OFFICIAL_LINKS.get(key)
        if not links:
            return ()
        return (links.get(i18n.UI_LANGUAGE) or links["en"],)

    @staticmethod
    def _language_score(link: LinkItem) -> int:
        parsed = urllib.parse.urlparse(link.url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        text = f"{link.name} {link.url}".lower()
        japanese = (
            domain.endswith(".jp")
            or domain.startswith(("jp.", "ja."))
            or "/jp/" in path
            or "/ja/" in path
            or any(keyword in text for keyword in ("日本", "公式", "攻略"))
        )
        english = (
            domain.startswith(("en.", "na.", "us."))
            or "/en/" in path
            or "/na/" in path
            or "/us/" in path
            or any(keyword in text for keyword in ("english", "official", "guide", "wiki"))
        )
        if i18n.UI_LANGUAGE == "ja":
            return 300 if japanese else -100 if english and not japanese else 0
        return 300 if english and not japanese else -100 if japanese else 0

    @staticmethod
    def _domain_matches(domain: str, domains: tuple[str, ...]) -> bool:
        return any(domain == item or domain.endswith(f".{item}") for item in domains)

    @staticmethod
    def _looks_official_forum(domain: str, text: str) -> bool:
        has_forum = any(keyword in text for keyword in ("forum", "forums", "community", "フォーラム"))
        has_official = any(keyword in text for keyword in ("official", "公式"))
        return has_forum and (has_official or domain.startswith(("forum.", "forums.", "community.")))

    @classmethod
    def _looks_official_site(cls, domain: str, text: str) -> bool:
        if cls._domain_matches(domain, cls.GUIDE_DOMAINS + cls.INFO_DOMAINS + cls.HIGH_TRAFFIC_DOMAINS):
            return False
        if any(keyword in text for keyword in ("forum", "forums", "community", "フォーラム")):
            return False
        return any(keyword in text for keyword in ("official site", "official website", "公式サイト", "公式ホームページ"))
