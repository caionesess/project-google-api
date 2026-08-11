from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCRIPT_DIR = Path(__file__).resolve().parent

CREDENTIALS_PATH = (
    SCRIPT_DIR.parent.parent
    / "credentials"
    / "google-service-account.json"
)

PASTA_RAIZ_ID = "ID_DA_PASTA_RAIZ" # Substitua pelo ID da pasta raiz do Google Drive

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]

DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.document"
)

DOC_MIME_TYPE = "application/vnd.google-apps.document"

DOC_MIME_TYPES_ORIGINAIS = [
    DOCX_MIME_TYPE,
    "application/msword",
]

creds = service_account.Credentials.from_service_account_file(
    CREDENTIALS_PATH,
    scopes=SCOPES,
)

service = build(
    "drive",
    "v3",
    credentials=creds,
)

total_pastas = 0
total_encontrados = 0
total_convertidos = 0
total_ja_existiam = 0
total_ignorados = 0
total_erros = 0

def listar_arquivos_da_pasta(pasta_id):
    """
    Retorna todos os arquivos diretamente dentro da pasta.
    """
    arquivos = []
    page_token = None

    query = (
        f"'{pasta_id}' in parents "
        f"and trashed = false"
    )

    while True:

        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        arquivos.extend(
            results.get("files", [])
        )

        page_token = results.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return arquivos

def listar_subpastas(pasta_id):
    """
    Retorna todas as subpastas diretamente dentro
    da pasta informada.
    """
    pastas = []
    page_token = None

    query = (
        f"'{pasta_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )

    while True:

        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        pastas.extend(
            results.get("files", [])
        )

        page_token = results.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return pastas


def listar_google_docs(pasta_id):
    """
    Retorna os Google Docs existentes diretamente
    dentro da pasta.
    """

    docs = {}
    page_token = None

    query = (
        f"'{pasta_id}' in parents "
        f"and mimeType = '{DOC_MIME_TYPE}' "
        f"and trashed = false"
    )

    while True:

        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        for file in results.get("files", []):

            docs[file["name"]] = file["id"]

        page_token = results.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return docs


def processar_pasta(pasta_id, pasta_nome, nivel=0):
    """
    Processa uma pasta e, recursivamente, todas as
    subpastas existentes dentro dela.
    """

    global total_pastas
    global total_encontrados
    global total_convertidos
    global total_ja_existiam
    global total_ignorados
    global total_erros

    total_pastas += 1

    indentacao = "    " * nivel

    print()
    print(
        f"{indentacao}{'=' * 60}"
    )

    print(
        f"{indentacao}📁 PASTA: {pasta_nome}"
    )

    print(
        f"{indentacao}   ID: {pasta_id}"
    )

    print(
        f"{indentacao}{'=' * 60}"
    )


    arquivos = listar_arquivos_da_pasta(
        pasta_id
    )

    docs_existentes = listar_google_docs(
        pasta_id
    )

    print(
        f"{indentacao}Arquivos encontrados: "
        f"{len(arquivos)}"
    )

    print(
        f"{indentacao}Google Docs existentes: "
        f"{len(docs_existentes)}"
    )

    for file in arquivos:

        file_id = file["id"]
        file_name = file["name"]
        mime_type = file["mimeType"]

        print()
        print(
            f"{indentacao}Encontrado: '{file_name}'"
        )

        print(
            f"{indentacao}MIME: {mime_type}"
        )

        if mime_type not in DOC_MIME_TYPES_ORIGINAIS:

            print(
                f"{indentacao}  └─ IGNORADO: "
                f"não é DOC/DOCX"
            )

            total_ignorados += 1

            continue

        total_encontrados += 1

        doc_name = Path(file_name).stem

        if doc_name in docs_existentes:

            print(
                f"{indentacao}  └─ JÁ EXISTE: "
                f"'{doc_name}'"
            )

            total_ja_existiam += 1

            continue

        try:

            print(
                f"{indentacao}  └─ Convertendo..."
            )

            body = {
                "name": doc_name,
                "parents": [pasta_id],
                "mimeType": DOC_MIME_TYPE,
            }

            converted_file = service.files().copy(
                fileId=file_id,
                body=body,
                supportsAllDrives=True,
                fields="id, name, mimeType",
            ).execute()

            converted_id = converted_file["id"]

            print(
                f"{indentacao}  └─ CONVERTIDO!"
            )

            print(
                f"{indentacao}     Nome: "
                f"{converted_file['name']}"
            )

            print(
                f"{indentacao}     ID: "
                f"{converted_id}"
            )

            docs_existentes[doc_name] = converted_id

            total_convertidos += 1

        except Exception as error:

            total_erros += 1

            print(
                f"{indentacao}  └─ ERRO AO CONVERTER:"
            )

            print(
                f"{indentacao}     {error}"
            )

    subpastas = listar_subpastas(
        pasta_id
    )

    print()

    if subpastas:

        print(
            f"{indentacao}Subpastas encontradas: "
            f"{len(subpastas)}"
        )

        for subpasta in subpastas:

            subpasta_id = subpasta["id"]
            subpasta_nome = subpasta["name"]

            processar_pasta(
                pasta_id=subpasta_id,
                pasta_nome=subpasta_nome,
                nivel=nivel + 1,
            )

    else:

        print(
            f"{indentacao}Nenhuma subpasta."
        )


def main(pasta_raiz_id=None):
    print()
    print("=" * 70)
    print("CONVERSOR DOC/DOCX → GOOGLE DOCS")
    print("=" * 70)

    print()
    print(
        f"Pasta raiz: {pasta_raiz_id or PASTA_RAIZ_ID}"
    )

    print()
    print(
        "Iniciando varredura recursiva..."
    )

    raiz = service.files().get(
        fileId=(pasta_raiz_id or PASTA_RAIZ_ID),
        fields="id, name, mimeType",
        supportsAllDrives=True,
    ).execute()


    processar_pasta(
        pasta_id=raiz["id"],
        pasta_nome=raiz["name"],
        nivel=0,
    )

    print()
    print()
    print("=" * 70)
    print("PROCESSAMENTO CONCLUÍDO")
    print("=" * 70)

    print()
    print(
        f"Pastas processadas:       {total_pastas}"
    )

    print(
        f"DOC/DOCX encontrados:     {total_encontrados}"
    )

    print(
        f"Convertidos:              {total_convertidos}"
    )

    print(
        f"Já possuíam Google Docs:  {total_ja_existiam}"
    )

    print(
        f"Ignorados:                {total_ignorados}"
    )

    print(
        f"Erros:                    {total_erros}"
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()