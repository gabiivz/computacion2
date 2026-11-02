import asyncio


async def ejecutar(params, ctx):
    # asyncio.sleep cede el control al loop; time.sleep() lo congelaría entero (clase 18)
    await asyncio.sleep(params["segundos"])
    return {"esperado_s": params["segundos"]}
