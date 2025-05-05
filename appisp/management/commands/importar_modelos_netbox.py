# appisp/management/commands/importar_modelos_netbox.py

import os
import shutil
import subprocess
from pathlib import Path
import yaml

from django.core.management.base import BaseCommand
from django.conf import settings

from appisp.models import Modelo, Fabricante, Interface


class Command(BaseCommand):
    help = 'Importa modelos de equipamentos do repositório da comunidade NetBox'

    def handle(self, *args, **options):
        repo_url = 'https://github.com/netbox-community/devicetype-library.git'
        base_dir = Path(settings.BASE_DIR)
        data_dir = base_dir / 'data'
        repo_dir = data_dir / 'devicetype-library'
        device_types_dir = repo_dir / 'device-types'
        media_modelos_dir = base_dir / 'media' / 'modelos'

        # Cria diretório se não existir
        media_modelos_dir.mkdir(parents=True, exist_ok=True)

        # Clonar repositório se ainda não existir
        if not repo_dir.exists():
            self.stdout.write(self.style.WARNING(f"Clonando repositório em: {repo_dir}"))
            subprocess.run(['git', 'clone', repo_url, str(repo_dir)], check=True)
        else:
            self.stdout.write(self.style.SUCCESS(f"Repositório já presente em: {device_types_dir}"))

        # Tentar fazer git lfs pull (ignorar erro se não tiver git-lfs)
        try:
            subprocess.run(['git', 'lfs', 'pull'], cwd=repo_dir, check=True)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Não foi possível executar 'git lfs pull': {e}"))

        # Importar arquivos .yaml
        for root, _, files in os.walk(device_types_dir):
            for arquivo in files:
                if not arquivo.endswith('.yaml'):
                    continue

                caminho_yaml = Path(root) / arquivo
                if not caminho_yaml.exists():
                    self.stdout.write(self.style.WARNING(f"Arquivo não encontrado: {caminho_yaml} — ignorando."))
                    continue

                try:
                    with open(caminho_yaml, 'r') as f:
                        dados = yaml.safe_load(f)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Erro ao ler {caminho_yaml}: {e}"))
                    continue

                fabricante_nome = dados.get('manufacturer')
                modelo_nome = dados.get('model')

                if not fabricante_nome or not modelo_nome:
                    self.stdout.write(self.style.WARNING(f"Dados incompletos em {caminho_yaml} — ignorando."))
                    continue

                fabricante, _ = Fabricante.objects.get_or_create(nome=fabricante_nome)

                modelo, criado = Modelo.objects.get_or_create(modelo=modelo_nome, fabricante=fabricante)

                if criado:
                    self.stdout.write(self.style.SUCCESS(f"Importado: {fabricante.nome} - {modelo_nome}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Modelo já existe: {fabricante.nome} - {modelo_nome}"))

                # Importar imagem, se houver
                imagem_path = caminho_yaml.with_suffix('.jpg')
                if imagem_path.exists():
                    nome_arquivo_destino = f"{fabricante_nome}_{modelo_nome}.jpg".replace(' ', '_')
                    destino = media_modelos_dir / nome_arquivo_destino
                    if not destino.exists():
                        shutil.copy(imagem_path, destino)
                        self.stdout.write(self.style.SUCCESS(f"Imagem copiada: {destino.name}"))
                    else:
                        self.stdout.write(self.style.NOTICE(f"Imagem já existe: {destino.name}"))

                # ✅ Importar interfaces
                interfaces = dados.get('interfaces', [])
                for iface in interfaces:
                    nome_iface = iface.get('name')
                    tipo_iface = iface.get('type', 'unknown')
                    mgmt = iface.get('mgmt_only', False)

                    if nome_iface:
                        if not Interface.objects.filter(modelo=modelo, nome=nome_iface).exists():
                            Interface.objects.create(
                                modelo=modelo,
                                nome=nome_iface,
                                tipo=tipo_iface,
                                mgmt_only=mgmt
                            )
                            self.stdout.write(self.style.SUCCESS(f"  ↳ Interface importada: {nome_iface}"))
                        else:
                            self.stdout.write(self.style.NOTICE(f"  ↳ Interface já existe: {nome_iface}"))
