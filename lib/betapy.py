#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""BetaPy - Librairie python pour Betaseries

Projet-url: http://betapy.googlecode.com

"""

import urllib
import urllib2
import hashlib
import urlparse
import json


class Beta:
    """Ensemble de fonctions utilisant l'API de BetaSeries.
    
    PROPOSITION 1: l'organisation des fonctions de base de la
    classe Beta() essaient de suivre les catégories établies par
    l'API de BetaSeries:
        * shows/
        * subtitles/
        * planning/
        * members/
        * comments/
        * timeline/

    PROPOSITION 2: on nomme les fonctions de la même manière que l'API de
    base en ajoutant le caractère underscore dans le but de faciliter les
    mises à jour:
        EXEMPLE:
        * show_search()
        * show_display()
        * subtitles_last()
        * subtitles_show()
        * ...

    PROPOSITION 3: Procédure pour construire les fonctions de base
    de la classe Beta():
        EXEMPLE:
            def shows_search(self, title):
                params = urllib.urlencode({'title': title})
                url = self.build.url("/shows/search", params)
                return self.build.data(url)
                
        EXPLICATION:
            # Si il y a des paramètres à l'url, ils utilisent urllib.urlencode()
            params = urllib.urlencode({'title': title})
            # on construit l'url à l'aide d'une fonction de la classe Builder
            url = self.build.url("/shows/search", params)
            # on retourne le contenu de la requête à l'aide d'une fonction de la classe Builder
            return self.build.data(url)

    """
    def __init__( self,
                  key="3c15b9796654",
                  user_agent="BetaPy",
                  format=None,
                  login=None,
                  password=None):
        """Initialisation des paramètres.
        
        Possibilités de spécifier:
          * une clé api individuelle
          * l'user-agent pour les requêtes
          * le format souhaité pour les retours de requêtes (xml ou json). Par
            défaut, le format de retour est un dictionnaire python.

        Pour définir le token une seule fois, l'attribuer à l'instance de Beta.
        Exemple:
          beta = betapy.Beta(login="dev001", password="developer")
          auth = beta.members_auth()
          token = auth['member']['token']
          beta.token = token
          print beta.planning_member()
        
        """
        # définition de la clé API utilisateur.
        self.key = str(key)
        # définition de l'User-Agent pour les requêtes
        self.user_agent = str(user_agent)
        # definition du format des retours de requêtes
        self.format = format
        # définition des identifiants de l'utilisateur
        self.login = login
        self.password = password
        # instanciation de la classe Builder pour le traitement des requêtes
        self.build = Builder(self.key, self.user_agent, self.format)
        # le token est à attribué lors à l'instanciation de la class Beta
        self.token = None


    def shows_search(self, title):
        """Liste les séries qui contiennent exactement la portion search dans leur titre.

        l'argument title doit avoir plus de 2 caractères.
        
        """
        params = urllib.urlencode({'title': title})
        url = self.build.url("/shows/search", params)
        return self.build.data(url)


    def shows_display(self, serie_url):
        """Donne des informations sur la série (identifiée par son url).

        Note : Si url est à all, la fonction retourne toutes les séries de BetaSeries.

        """
        url = self.build.url("/shows/display/%s" % serie_url)
        return self.build.data(url)


    def subtitles_last(self, number="", language=""):
        """Affiche les derniers sous-titres récupérés par BetaSeries,
        dans la limite de 100.

        Possibilité de spécifier la langue et/ou une série en particulier.

        """
        params = urllib.urlencode({'number': number,
                                   'language': language})
        url = self.build.url("/subtitles/last", params)
        return self.build.data(url)


    def subtitles_show(self, serie, season="", episode="", language="", file_=""):
        """Affiche les sous-titres récupérés par BetaSeries d'une certaine série,
        dans la limite de 100.

        Possibilité de spécifier la langue et/ou une saison, un épisode en particulier.

        Vous pouvez récupérer des sous-titres directement grâce au nom des fichiers vidéo.

        """
        #si l'utilisateur entre un nom de fichier vidéo
        if file_:
            params = urllib.urlencode({'file': file_,
                                       'language': language})
            url = self.build.url("/subtitles/show", params)
        else:
            params = urllib.urlencode({'season': season,
                                       'episode': episode,
                                       'language': language})
            url = self.build.url("/subtitles/show/%s" % serie, params)
        return self.build.data(url)


    def planning_general(self):
        """Affiche tous les épisodes diffusés les 8 derniers jours
        jusqu'aux 8 prochains jours.

        """
        url = self.build.url("/planning/general")
        return self.build.data(url)

        
    def planning_member(self, login="", view=""):
        """Affiche le planning du membre identifié ou d'un autre membre.
        
        L'accès varie selon les options vie privée de chaque membre).
        Vous pouvez rajouter le paramètre view pour n'afficher que les épisodes encore non-vus.

        """
        if login:
            login = "/%s" % login
            params = urllib.urlencode({'view' : view})
        else:
            params = urllib.urlencode({'token': self.token,
                                       'view' : view})

        url = self.build.url("/planning/member%s" % login, params)
        return self.build.data(url)
        

    def members_auth(self):
        """Identifie le membre avec son login et le hash MD5.

        Retourne le token à utiliser pour les requêtes futures.

        """
        # hash MD5 du mot de passe
        hash_pass = hashlib.md5(self.password).hexdigest()
        # paramètres de l'url
        params = urllib.urlencode({'login': self.login, 'password': hash_pass})
        url = self.build.url("/members/auth", params)
        return self.build.data(url)


    def members_is_active(self, token):
        """Vérifie si le token spécifié est actif."""
        params = urllib.urlencode({'token': token})
        url = self.build.url("/members/is_active", params)
        return self.build.data(url)


    def members_destroy(self):
        """Vérifie si le token spécifié est actif."""
        params = urllib.urlencode({'token': self.token})
        url = self.build.url("/members/destroy", params)
        return self.build.data(url)


    def members_infos(self, login="", nodata=1, since=None):
        """Renvoie les informations principales du membre identifié ou d'un autre membre."""
        # si le nom d'un utilisateur est fourni, on ajoute le paramètre
        if login:
            login = "/%s" % login
        params = urllib.urlencode({'token': self.token,
                                   'nodata' : nodata,
                                   'since' : since})
        url = self.build.url("/members/infos%s" % login, params)
        return self.build.data(url)


    def members_options(self):
        """Retourne les options du membre."""
        params = urllib.urlencode({'token': self.token})
        url = self.build.url("/members/options", params)
        return self.build.data(url)



class Builder:
    """Ensemble de fonctions utiles pour le traitement des requêtes vers l'API.
    
    Fonctionnalités:
      * Construction des url.
      * Récupération du contenu des requêtes.
      * Traitement des requêtes.

    """
    def __init__(self,
                 key=None,
                 user_agent=None,
                 format=None):
        """Initialisation des paramètres."""
        # définition de la clé API utilisateur.
        self.key = key
        # définition de l'User-Agent pour les requêtes
        self.user_agent = user_agent
        # definition du format des retours de requêtes
        self.format = format


    def url(self, method, params=None):
        """Constructeur d'url pour les requêtes vers l'API.

        Exemple:
        >>> self.build_url("/members/auth", "login=Dev001&password=hash_md5")
        http://api.betaseries.com/members/auth.json?key=3c5b...&login=Dev001&password=5e8...

        """
        scheme = 'http'
        # url de l'api
        netloc = 'api.betaseries.com'
        # methode de l'api avec le format de retour souhaité (xml|json)
        format = self.format
        # exception si l'utilisateur n'entre pas de format, ce sera un dict()
        if not self.format:
            # utilisation du json pour la fonction data() par facilité.
            format = "json"
        path = '%s.%s' % (method, format)
        # insertion de la clé api
        param_key = "key=%s" % self.key
        # construction des paramètres de l'url
        query = '%s&%s' % (param_key, params)
        # retourne l'ensemble de l'url
        return urlparse.urlunparse((scheme, netloc, path,
                                    None, query, None))

    def get_source(self, url):
        """Retourne le contenu renvoyé à partir d'une requête url.

        La fonction permet également de créer l'user-agent.

        """
        opener = urllib2.build_opener()
        # ajout de l'user-agent
        opener.addheaders = [('User-agent', self.user_agent)]
        source = opener.open(url)
        # retourne le contenu
        return source.read()


    def data(self, url):
        """Converti les retours de requêtes en données communément exploitables.

        Proposition: tout transformer en dictionnaire python par défaut.
        
        Si l'utilisateur souhaite le retour en xml ou en json, il est retourné

        """
        # récupération du contenu à partir d'une requête url
        source = self.get_source(url)
        # si le format de retour souhaité est le json ou xml
        if self.format in ['xml', 'json']:
            return source
        # si l'utilisateur n'a pas entré de format OU souhaite un dictionnaire
        else:
            json_data = json.loads(source)
            # retourne le contenu sous forme de dictionnaire Python
            return json_data['root']

