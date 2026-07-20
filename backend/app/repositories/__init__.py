"""
Capa de repositorios (Fase 2 de la refactorizacion).

Objetivo: sacar el SQL crudo de los endpoints (routers finos) y concentrarlo
en modulos de acceso a datos, testeables y reutilizables.
Los routers quedan delgados: validan, llaman al repo, orquestan y serializan.
"""
