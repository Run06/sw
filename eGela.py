# -*- coding: UTF-8 -*-
import re
from tkinter import messagebox
import requests
import urllib
from urllib.parse import unquote
from bs4 import BeautifulSoup
import time

import helper

class eGela:
    _login = 0
    _cookie = ""
    _curso = ""
    _refs = []
    _root = None

    def __init__(self, root):
        self._root = root

    def check_credentials(self, username, password, event=None):
        popup, progress_var, progress_bar = helper.progress("check_credentials", "Logging into eGela...")
        progress = 0
        progress_var.set(progress)
        progress_bar.update()

        print("##### 1. PETICION #####")
        metodo = 'GET'
        uri = "https://egela.ehu.eus/login/index.php"
        print("GET " + uri)
        cabeceras = {'Host': "egela.ehu.eus"}

        res = requests.request(metodo, uri, headers=cabeceras, allow_redirects=False)

        # Código de estado HTTP
        codigo = res.status_code
        # Texto descriptivo del código
        descripcion = res.reason
        print(str(codigo) + " " + descripcion)

        self._cookie = res.headers['Set-Cookie'].split(';')[0]
        print("Cookie: " + self._cookie)
        soup = BeautifulSoup(res.content, 'html.parser')
        logintoken = soup.find('input', attrs={'name': 'logintoken'})['value']
        print("Logintoken: " + logintoken)

        progress = 25
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)


        print("\n##### 2. PETICION #####")
        metodo = 'POST'
        uri = "https://egela.ehu.eus/login/index.php"
        print("POST " + uri)
        print("Credenciales: User =  " + username.get() + " Password = " + password.get())
        cabeceras = {
            'Host': "egela.ehu.eus",
            'Cookie': self._cookie,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        cuerpo = {
            "logintoken": logintoken,
            "username": username.get(),
            "password": password.get()
        }
        cuerpo_encoded = urllib.parse.urlencode(cuerpo)

        res = requests.request(metodo, uri, headers=cabeceras, data=cuerpo_encoded, allow_redirects=False)

        # Código de estado HTTP
        codigo = res.status_code
        # Texto descriptivo del código
        descripcion = res.reason
        print(str(codigo) + " " + descripcion)

        try:
            self._cookie = res.headers['Set-Cookie'].split(';')[0]
        except Exception as e:
            print("Error obteniendo la cookie: " + str(e))

        location = res.headers['Location']

        print("Cookie: " + self._cookie)
        print("Location: " + location)

        progress = 50
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)

        print("\n##### 3. PETICION #####")
        metodo = 'GET'
        uri = location
        print("POST " + uri)
        cabeceras = {'Host': "egela.ehu.eus",
                     'Cookie': self._cookie}

        res = requests.request(metodo, uri, headers=cabeceras, allow_redirects=False)

        codigo = res.status_code
        # Texto descriptivo del código
        descripcion = res.reason
        print(str(codigo) + " " + descripcion)
        try:
            location = res.headers['Location']
            print("Location: " + location)
        except Exception as e:
            print("Error obteniendo la location: " + str(e))

        progress = 75
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)
        popup.destroy()

        print("\n##### 4. PETICION #####")
        print("Comprobar sesión!!!")
        metodo = 'GET'
        uri = "https://egela.ehu.eus/user/profile.php"
        print("GET " + uri)
        cabeceras = {'Host': "egela.ehu.eus",
                     'Cookie': self._cookie}
        cuerpo = ""

        res = requests.request(metodo, uri, headers=cabeceras, data=cuerpo, allow_redirects=False)
        COMPROBACION_DE_LOG_IN = res.status_code

        # Código de estado HTTP
        codigo = COMPROBACION_DE_LOG_IN
        # Texto descriptivo del código
        descripcion = res.reason
        print(str(codigo) + " " + descripcion)

        progress = 100
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)
        popup.destroy()

        if COMPROBACION_DE_LOG_IN == 200:
            self._login = 1
            soup = BeautifulSoup(res.content, "html.parser")
            curso_tag = soup.find("a", string=lambda t: t and "Sistemas Web" in t)
            if curso_tag:
                self._curso = curso_tag['href']
            self._root.destroy()
        else:
            messagebox.showinfo("Alert Message", "Login incorrect!")

    def get_pdf_refs(self):
        popup, progress_var, progress_bar = helper.progress("get_pdf_refs", "Downloading PDF list...")
        progress = 0
        progress_var.set(progress)
        progress_bar.update()

        print("\n##### 4. PETICION (Página principal de la asignatura en eGela) #####")
        metodo = 'GET'
        uri = self._curso
        cabeceras = {'Host': "egela.ehu.eus", 'Cookie': self._cookie}

        res_main = requests.get(self._curso, headers=cabeceras)
        soup_main = BeautifulSoup(res_main.content, "html.parser")

        # buscar todos los enlaces
        secciones = {}
        enlaces = soup_main.find_all('a', href=True)
        for link in enlaces:
            href = link['href']

            match = re.search(r'section=(\d+)', href)
            if match:
                section_id = match.group(1)

                if section_id not in secciones:
                    secciones[section_id] = f"{self._curso}&section={section_id}"

        secciones = list(secciones.values())

        # usamos al menos la principal
        if not secciones:
            secciones = [self._curso]

        print(f"Se han detectado {len(secciones)} secciones automáticas.")

        # visitar cada sección y extraer PDFs
        for index, url_seccion in enumerate(secciones):
            print(f"Procesando sección {index + 1}...")
            res = requests.get(url_seccion, headers=cabeceras)
            soup = BeautifulSoup(res.content, "html.parser")

            actividades = soup.find_all('div', {'class': 'activity-instance d-flex flex-column'})

            for act in actividades:
                img = act.find('img')
                if img and 'pdf' in img.get('src', ''):
                    a = act.find('a')
                    if a:
                        enlace_pdf = a['href']
                        nombre_pdf = a.find('span').text.split(' Archivo')[0].split(' Fitxategia')[0].strip()

                        # Evitar duplicados si un PDF aparece en varias vistas
                        if not any(d['pdf_name'] == nombre_pdf for d in self._refs):
                            self._refs.append({'pdf_name': nombre_pdf, 'link': enlace_pdf})

            # Actualizar progreso segun seccion
            progress = float((index + 1) / len(secciones)) * 100
            progress_var.set(progress)
            progress_bar.update()

        popup.destroy()
        return self._refs

    def get_pdf(self, selection):

        print("\t##### descargando PDF... #####")

        try:

            # selection puede venir como tuple -> (0,)
            if isinstance(selection, tuple):
                selection = selection[0]

            # Si viene índice
            if isinstance(selection, int):

                if selection < 0 or selection >= len(self._refs):
                    print("Índice fuera de rango.")
                    return "error.pdf", b""

                ref = self._refs[selection]

            else:
                # Buscar por nombre
                ref = next(
                    (r for r in self._refs if r['pdf_name'] == selection),
                    None
                )

            if not ref:
                print("PDF no encontrado.")
                return "error.pdf", b""

            target_link = ref['link']
            pdf_name = ref['pdf_name'] + ".pdf"

            cabeceras = {'Cookie': self._cookie}

            res = requests.get(
                target_link,
                headers=cabeceras,
                allow_redirects=False
            )

            # Seguir redirects
            if res.status_code in (301, 302, 303, 307, 308):

                new_uri = res.headers.get('Location')

                if not new_uri:
                    print("Redirect sin Location")
                    return "error.pdf", b""

                res = requests.get(
                    new_uri,
                    headers=cabeceras
                )

            if res.status_code != 200:
                print(f"HTTP ERROR {res.status_code}")
                return "error.pdf", b""

            pdf_content = res.content

            if not pdf_content:
                print("PDF vacío")
                return "error.pdf", b""

            return pdf_name, pdf_content

        except Exception as e:

            print(f"Error descargando PDF: {e}")

            return "error.pdf", b""