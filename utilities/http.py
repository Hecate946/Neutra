class Utils:
    ##############################
    ## Aiohttp Helper Functions ##
    ##############################

    def __init__(self, session):
        self.session = session

    async def query(self, url, method="get", res_method="text", *args, **kwargs):
        async with getattr(self.session, method.lower())(url, *args, **kwargs) as res:
            return await getattr(res, res_method)()

    async def get(self, url, *args, **kwargs):
        return await self.query(url, "get", *args, **kwargs)

    async def post(self, url, *args, **kwargs):
        return await self.query(url, "post", *args, **kwargs)

    async def put(self, url, *args, **kwargs):
        return await self.query(url, "put", *args, **kwargs)

    async def patch(self, url, *args, **kwargs):
        return await self.query(url, "patch", *args, **kwargs)
