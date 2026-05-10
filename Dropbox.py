import requests
import urllib
import webbrowser
from socket import AF_INET, socket, SOCK_STREAM
import json
import helper

app_key = 'f8wu903crfyp2ex'
app_secret = 'ynjhsiv5muh98gx'
server_addr = "localhost"
server_port = 8070
redirect_uri = "http://" + server_addr + ":" + str(server_port)

#files.metadata.read ON
#files.content.write ON
#files.content.read ON

class Dropbox:
    _access_token = ""
    _path = "/"
    _files = []
    _root = None
    _msg_listbox = None

    def __init__(self, root):
        self._root = root

    def local_server(self):
        # por el puerto 8090 esta escuchando el servidor que generamos
        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.bind((server_addr, server_port))
        server_socket.listen(1)
        print("\tLocal server listening on port " + str(server_port))

        # recibe la redireccio 302 del navegador
        client_connection, client_address = server_socket.accept()
        peticion = client_connection.recv(1024)
        print("\tRequest from the browser received at local server:")
        print (peticion)

        # buscar en solicitud el "auth_code"
        primera_linea =peticion.decode('UTF8').split('\n')[0]
        aux_auth_code = primera_linea.split(' ')[1]
        auth_code = aux_auth_code[7:].split('&')[0]
        print ("\tauth_code: " + auth_code)

        # devolver una respuesta al usuario
        http_response = "HTTP/1.1 200 OK\r\n\r\n" \
                        "<html>" \
                        "<head><title>Proba</title></head>" \
                        "<body>The authentication flow has completed. Close this window.</body>" \
                        "</html>"
        client_connection.sendall(http_response.encode('utf-8'))
        client_connection.close()
        server_socket.close()

        return auth_code

    def do_oauth(self):
        servidor = 'www.dropbox.com'
        params = {'response_type': 'code',
                  'client_id': app_key,
                  'redirect_uri': redirect_uri}
        params_encoded = urllib.parse.urlencode(params)
        recurso = '/oauth2/authorize?' + params_encoded
        uri = 'https://' + servidor + recurso
        webbrowser.open_new(uri)

        auth_code = self.local_server()

        if not auth_code:
            print("No se pudo obtener el código de autorización.")
            return

        ###################################################################################
        # ACCESS_TOKEN: Obtener el TOKEN https://www.api.dropboxapi.com/1/oauth2/token #
        ###################################################################################
        params = {'code': auth_code,
                  'grant_type': 'authorization_code',
                  'client_id': app_key,
                  'client_secret': app_secret,
                  'redirect_uri': redirect_uri}
        cabeceras = {'User-Agent': 'Python Client',
                     'Content-Type': 'application/x-www-form-urlencoded'}
        uri = 'https://api.dropboxapi.com/oauth2/token'
        respuesta = requests.post(uri, headers=cabeceras, data=params)
        print(respuesta.status_code)
        json_respuesta = json.loads(respuesta.content)
        self._access_token = json_respuesta['access_token']
        print("Access_Token:" + self._access_token)

        self._root.destroy()

    def list_folder(self, msg_listbox):
        print("/list_folder")
        uri = 'https://api.dropboxapi.com/2/files/list_folder'

        # Aseguramos que el path sea el esperado por la API
        path_to_send = "" if self._path == "/" else self._path
        datos = {'path': path_to_send}
        datos_encoded = json.dumps(datos)

        cabeceras = {
            'Authorization': 'Bearer ' + self._access_token,
            'Content-Type': 'application/json'
        }

        respuesta = requests.post(uri, headers=cabeceras, data=datos_encoded)

        # LOG DE SEGURIDAD
        if respuesta.status_code != 200:
            print(f"Error en Dropbox API: {respuesta.status_code}")
            print(f"Respuesta del servidor: {respuesta.text}")
            return  # Salimos para evitar el crash del JSON

        try:
            contenido_json = respuesta.json()
            self._files = helper.update_listbox2(msg_listbox, self._path, contenido_json)
        except Exception as e:
            print(f"Error decodificando JSON: {e}")

    def transfer_file(self, file_path, file_data):
        print("/upload")
        uri = 'https://content.dropboxapi.com/2/files/upload'
        # https://www.dropbox.com/developers/documentation/http/documentation#files-upload
        arg = {
            "path": file_path,
            "mode": "overwrite",
            "mute": False
        }
        cabeceras = {
            "Authorization": "Bearer " + self._access_token,
            "Dropbox-API-Arg": json.dumps(arg),
            "Content-Type": "application/octet-stream"
        }

        respuesta = requests.post(uri, headers=cabeceras, data=file_data)
        if respuesta.status_code == 200:
            print(f"Archivo {file_path} subido con éxito.")
        else:
            print("Error en upload: ", respuesta.text)

    def delete_file(self, file_path):
        print("/delete_file")
        uri = 'https://api.dropboxapi.com/2/files/delete_v2'
        # https://www.dropbox.com/developers/documentation/http/documentation#files-delete
        cabeceras = {
            'Authorization': 'Bearer ' + self._access_token,
            'Content-Type': 'application/json'
        }
        datos = {"path": file_path}

        respuesta = requests.post(uri, headers=cabeceras, data=json.dumps(datos))
        if respuesta.status_code == 200:
            print(f"Eliminado: {file_path}")
        else:
            print("Error al eliminar: ", respuesta.text)

    def create_folder(self, path):
        print("/create_folder")
        uri = 'https://api.dropboxapi.com/2/files/create_folder_v2'
        # https://www.dropbox.com/developers/documentation/http/documentation#files-create_folder
        cabeceras = {
            'Authorization': 'Bearer ' + self._access_token,
            'Content-Type': 'application/json'
        }
        datos = {
            "path": path,
            "autorename": False
        }

        respuesta = requests.post(uri, headers=cabeceras, data=json.dumps(datos))
        if respuesta.status_code == 200:
            print(f"Carpeta creada: {path}")
        else:
            print("Error al crear carpeta: ", respuesta.text)

    def download_file(self, file_path):
        print("/download")
        # https://www.dropbox.com/developers/documentation/http/documentation#files-download
        uri = 'https://content.dropboxapi.com/2/files/download'
        arg = {"path": file_path}
        cabeceras = {
            "Authorization": "Bearer " + self._access_token,
            "Dropbox-API-Arg": json.dumps(arg)
            #Aqui no hay que poner Content-Type ya que la API lo exige asi
        }
        respuesta = requests.post(uri, headers=cabeceras)
        if respuesta.status_code == 200:
            print(f"Archivo {file_path} descargado correctamente")
            return respuesta.content   # bytes del fichero
        else:
            print("Error en download: ", respuesta.text)
            return None