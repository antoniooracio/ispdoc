import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from appisp.models import Modelo

class Command(BaseCommand):
    help = 'Importa imagens frontais e traseiras dos modelos existentes no banco, se disponíveis no repositório'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repo',
            default='data/devicetype-library',
            help='Caminho para o repositório devicetype-library clonado'
        )

    def handle(self, *args, **options):
        repo_root = Path(options['repo'])
        images_dir = repo_root / 'device-type-images'
        media_dest = Path(settings.MEDIA_ROOT) / 'modelos'
        media_dest.mkdir(parents=True, exist_ok=True)

        modelos = Modelo.objects.all()
        total_atualizados = 0

        for modelo in modelos:
            fabricante_path = modelo.fabricante.nome.lower().replace(" ", "_")
            modelo_filename = modelo.modelo.lower().replace(" ", "_")

            front_src = images_dir / fabricante_path / f"{modelo_filename}_front.png"
            rear_src = images_dir / fabricante_path / f"{modelo_filename}_rear.png"

            alterado = False

            if front_src.exists() and not modelo.imagem_frontal:
                front_dest = media_dest / front_src.name
                shutil.copy(front_src, front_dest)
                modelo.imagem_frontal = f"modelos/{front_src.name}"
                alterado = True

            if rear_src.exists() and not modelo.imagem_traseira:
                rear_dest = media_dest / rear_src.name
                shutil.copy(rear_src, rear_dest)
                modelo.imagem_traseira = f"modelos/{rear_src.name}"
                alterado = True

            if alterado:
                modelo.save()
                self.stdout.write(self.style.SUCCESS(f"Imagens adicionadas: {modelo}"))
                total_atualizados += 1

        self.stdout.write(self.style.SUCCESS(f"{total_atualizados} modelos atualizados com imagens."))
