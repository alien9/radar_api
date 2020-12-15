from django.db import models
from django.contrib.gis.db import models as g

# Create your models here.
class Radar(models.Model):
    class Meta:
        verbose_name="Sensor"
        db_table = "base_radares"
    lote=models.IntegerField()
    codigo=models.TextField(max_length=50)
    endereco=models.TextField(max_length=400)
    sentido=models.TextField(max_length=200)
    referencia=models.TextField(max_length=100)
    tipo_equip=models.TextField(max_length=50)
    enquadrame=models.TextField(max_length=20)
    qtde_fxs_f=models.IntegerField()
    data_publi=models.TextField(max_length=50)
    velocidade=models.TextField(max_length=30)
    geom=g.PointField(srid=4326)
    bairro=models.TextField(max_length=300)
    velocidade_cam_oni=models.IntegerField()
    velocidade_carro_moto=models.IntegerField()
    data_publicacao=models.DateField()

class Viagem(models.Model):
    class Meta:
        verbose_name="Viagem"
        db_table = "viagens"
    inicio=models.IntegerField()
    data_inicio=models.DateTimeField()
    final=models.IntegerField()
    data_final=models.DateTimeField()
    tipo=models.IntegerField()

class Trajeto(models.Model):
    class Meta:
        verbose_name="Trajeto"
        db_table = "trajetos"
    viagem = models.ForeignKey(Viagem, null=True, on_delete=models.SET_NULL)
    tipo=models.IntegerField()
    data_inicio=models.DateTimeField()
    data_final=models.DateTimeField()
    origem=models.IntegerField()
    destino=models.IntegerField()
    v0=models.IntegerField()
    v1=models.IntegerField()

class Contagem(models.Model):
    class Meta:
        verbose_name="Contagem"
        db_table = "contagens"
    localidade=models.IntegerField()
    faixa=models.IntegerField()
    tipo=models.IntegerField()
    contagem=models.IntegerField()
    autuacoes=models.IntegerField()
    placas=models.IntegerField()
    data_e_hora=models.DateTimeField()

class Route(models.Model):
    class Meta:
        verbose_name="Rotas"
        db_table = "route"
    origem=models.IntegerField()
    destino=models.IntegerField()
    dist=models.FloatField()
    