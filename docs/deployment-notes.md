
## Instalar miniconda 3 

instalar el entorno conda usando environment.yml 

conda env create -f environment.yml -n iganima-test 


# Instalación - Nota técnica

## Problema

Al crear un entorno Conda manualmente, los canales definidos en `environment.yml` no se aplican automáticamente a las instalaciones posteriores con `conda install`.

## Síntoma

Paquetes como `obspy` no se encuentran o Conda tarda demasiado intentando resolver dependencias.

## Solución

Configurar `conda-forge` como canal principal antes de instalar paquetes manualmente:

```bash
conda config --add channels conda-forge
conda config --set channel_priority strict
```

Luego instalar normalmente:

```bash
conda install obspy
```

## Lección aprendida

`environment.yml` define los canales para la creación del entorno. Si posteriormente se instalan paquetes manualmente, Conviene verificar que los canales estén configurados correctamente, especialmente cuando el proyecto depende de `conda-forge`.