from django.db import models

# Create your models here.

class Impianto(models.Model):
    nome_impianto = models.CharField(max_length=100)
    nickname = models.CharField(max_length=50)
    # Altri campi...

    def __str__(self):
        return self.nome_impianto
