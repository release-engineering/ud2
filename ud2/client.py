# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, see <http://www.gnu.org/licenses/>.

"""
Primary client for interacting with UDv2 REST endpoints.
"""


import logging
from typing import Any, Dict, Iterator, List, Optional, Type

try:
    from typing import get_args, get_origin

except ImportError:
    # Python 3.7 compatibility
    def get_origin(annotation: Any) -> Optional[Any]:
        return getattr(annotation, '__origin__', None)


    def get_args(annotation: Any) -> tuple:
        return getattr(annotation, '__args__', ())

import requests
from pydantic import BaseModel

from .config import UDConfig
from .models import (PaginatedProducts, PaginatedRepositories,
                     PaginatedRepositoryResults, PaginatedVersions,
                     Product, ProductCreate, Repository, RepositoryCreate,
                     ResponseVersions, Version, VersionCreate)


logger = logging.getLogger('UDClient')


class UDClient:
    """
    REST client bound to a user configuration.
    """

    def __init__(self, config: UDConfig, session: Optional[requests.Session] = None) -> None:
        """
        Initialize the client with the given configuration.

        Note that if a session is provided, it will be used as is and settings
        from the configuration will be ignored.

        :param config: Resolved configuration detailing server and client certificate information.
        :param session: Optional pre-configured requests session
        """

        self._config = config

        logger.debug(f"config.name: {config.name}")
        logger.debug(f"config.base_url: {config.base_url}")
        logger.debug(f"config.client_cert: {config.client_cert}")
        logger.debug(f"config.client_key: {config.client_key}")
        logger.debug(f"config.ca_cert: {config.ca_cert}")
        logger.debug(f"config.verify: {config.verify}")
        logger.debug(f"config.timeout: {config.timeout}")

        self._timeout = config.timeout
        self._base_url = config.base_url.rstrip('/')

        if session:
            logger.debug("Using provided session")
        else:
            logger.debug("Creating new session")

            session = requests.Session()
            session.cert = (
                str(config.client_cert),
                str(config.client_key),
            )
            session.headers.setdefault('Accept', 'application/json')
            session.headers.setdefault('Content-Type', 'application/json')
            if config.ca_cert is not None:
                verify = str(config.ca_cert)
            else:
                verify = config.verify
            session.verify = verify

        self._session = session


    def _GET(self, path: str, **kwargs: Any) -> Any:
        """
        Make a GET request to the given path.
        """

        return self._request('GET', path, **kwargs)


    def _POST(self, path: str, **kwargs: Any) -> Any:
        """
        Make a POST request to the given path.
        """

        return self._request('POST', path, **kwargs)


    def _PUT(self, path: str, **kwargs: Any) -> Any:
        """
        Make a PUT request to the given path.
        """

        return self._request('PUT', path, **kwargs)


    def _DELETE(self, path: str, **kwargs: Any) -> Any:
        """
        Make a DELETE request to the given path.
        """

        return self._request('DELETE', path, **kwargs)


    def page_products(
            self,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None) -> PaginatedProducts:
        """
        Retrieve a single page of products.

        :param page: Page number used for pagination.
        :param limit: Items per page for pagination.
        :param sort: Optional sort order (`asc`, `desc`).
        """

        params = self._build_list_params(page=page, limit=limit, sort=sort)

        return self._GET('/products', params=params, model=PaginatedProducts)


    def iter_products(
            self,
            sort: Optional[str] = None,
            page_size: Optional[int] = 100) -> Iterator[Product]:
        """
        Iterate over products, lazily requesting additional pages.

        :param sort: Optional sort order (`asc`, `desc`).
        :param page_size: Items per page for pagination. Defaults to 100.
        """

        next_page = 1

        while True:
            page_obj = self.page_products(
                page=next_page,
                limit=page_size,
                sort=sort,
            )

            yield from page_obj.data

            # the API may have downgraded the page size, so we need to use the
            # actual page size in our checks and future calls.
            page_size = page_obj.limit

            if page_obj.page >= page_obj.total_pages:
                break

            # safety net.
            if len(page_obj.data) < page_size:
                break

            next_page = page_obj.page + 1


    def list_products(
            self,
            sort: Optional[str] = None,
            page_size: Optional[int] = None) -> List[Product]:
        """
        Collect products into a list, automatically iterating all pages when pagination is unset.

        :param sort: Optional sort order (`asc`, `desc`).
        :param page_size: Items per page for pagination.

        :returns: List of products.
        """

        return list(self.iter_products(sort=sort, page_size=page_size))


    def create_product(self, payload: ProductCreate) -> Product:
        """
        Create a product resource.

        :param payload: Product payload matching API expectations.
        :returns: Newly created product.
        """

        return self._POST(
            '/products',
            payload=payload,
            model=Product,
            unwrap_data=True,
        )


    def get_product(self, product_id: int) -> Product:
        """
        Retrieve a product by identifier.

        :param product_id: Product identifier.
        :returns: Product representation.
        """

        return self._GET(
            f'/products/{product_id}',
            model=Product,
            unwrap_data=True,
        )


    def update_product(self, product_id: int, payload: ProductCreate) -> Product:
        """
        Update an existing product.

        :param product_id: Product identifier.
        :param payload: Updated product payload.
        :returns: Updated product.
        """

        return self._PUT(
            f'/products/{product_id}',
            payload=payload,
            model=Product,
            unwrap_data=True,
        )


    def delete_product(self, product_id: int) -> None:
        """
        Delete a product.

        :param product_id: Product identifier.
        """

        self._DELETE(f'/products/{product_id}')


    def search_products(
            self,
            name: Optional[str] = None,
            eng_id: Optional[int] = None,
            page: Optional[int] = None,
            limit: Optional[int] = None) -> PaginatedProducts:
        """
        Search products by name and/or engineering ID.

        :param name: Product name (partial, case-insensitive).
        :param eng_id: Engineering ID (exact match, must be > 0).
        :param page: Page number used for pagination.
        :param limit: Items per page for pagination.
        :returns: Paginated product results.
        """

        params = self._build_search_params(
            page=page,
            limit=limit,
            name=name,
            eng_id=eng_id,
        )
        return self._GET('/products/search', params=params, model=PaginatedProducts)


    def list_product_versions(self, product_id: int) -> List[Version]:
        """
        Retrieve versions for a product.

        :param product_id: Product identifier.
        :returns: Versions associated with the product, ordered by ID ascending.
        """

        response = self._GET(
            f'/products/{product_id}/product_versions',
            model=ResponseVersions,
        )

        return sorted(response.data, key=lambda v: v.id)


    def create_product_version(
            self,
            product_id: int,
            payload: VersionCreate) -> Version:
        """
        Create a product version.

        :param product_id: Product identifier.
        :param payload: Version payload.
        :returns: Newly created version.
        """

        return self._POST(
            f'/products/{product_id}/product_versions',
            payload=payload,
            model=Version,
            unwrap_data=True,
        )


    def get_product_version(self, version_id: int) -> Version:
        """
        Retrieve a product version.

        :param version_id: Version identifier.
        :returns: Version representation.
        """

        return self._GET(
            f'/product_versions/{version_id}',
            model=Version,
            unwrap_data=True,
        )


    def update_product_version(
            self,
            version_id: int,
            payload: VersionCreate) -> Version:
        """
        Update a product version.

        :param version_id: Version identifier.
        :param payload: Updated version payload.
        :returns: Updated version.
        """

        return self._PUT(
            f'/product_versions/{version_id}',
            payload=payload,
            model=Version,
            unwrap_data=True,
        )


    def delete_product_version(self, version_id: int) -> None:
        """
        Delete a product version.

        :param version_id: Version identifier.
        """

        self._DELETE(f'/product_versions/{version_id}')


    def search_product_versions(
            self,
            version: Optional[str] = None,
            product_id: Optional[int] = None,
            cpe: Optional[str] = None,
            page: Optional[int] = None,
            limit: Optional[int] = None) -> PaginatedVersions:
        """
        Search product versions by version, CPE, and/or product ID.

        :param version: Version string (glob pattern, case-insensitive).
        :param product_id: Product ID (exact match, must be > 0).
        :param cpe: CPE string (glob pattern, case-insensitive).
        :param page: Page number used for pagination.
        :param limit: Items per page for pagination.
        :returns: Paginated product version results.
        """

        params = self._build_search_params(
            page=page,
            limit=limit,
            version=version,
            product_id=product_id,
            cpe=cpe,
        )

        return self._GET(
            '/product_versions/search',
            params=params,
            model=PaginatedVersions,
        )


    def page_repositories(
            self,
            product_version_id: int,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None) -> PaginatedRepositories:
        """
        Retrieve a single page of repositories for a product version.

        :param product_version_id: Product version identifier.
        :param page: Page number used for pagination.
        :param limit: Items per page for pagination.
        :param sort: Optional sort order (`asc`, `desc`).
        """

        params = self._build_list_params(page=page, limit=limit, sort=sort)

        return self._GET(
            f'/product_versions/{product_version_id}/files',
            params=params,
            model=PaginatedRepositories,
        )


    def iter_repositories(
            self,
            product_version_id: int,
            sort: Optional[str] = None,
            page_size: Optional[int] = 100) -> Iterator[Repository]:
        """
        Iterate over repositories for a product version, lazily requesting additional pages.

        :param product_version_id: Product version identifier.
        :param sort: Optional sort order (`asc`, `desc`).
        :param page_size: Items per page for pagination. Defaults to 100.
        """

        next_page = 1

        while True:
            page_obj = self.page_repositories(
                product_version_id=product_version_id,
                page=next_page,
                limit=page_size,
                sort=sort,
            )

            yield from page_obj.data

            # the API may have downgraded the page size, so we need to use the
            # actual page size in our checks and future calls.
            page_size = page_obj.limit

            if page_obj.page >= page_obj.total_pages:
                break

            # safety net.
            if len(page_obj.data) < page_size:
                break

            next_page = page_obj.page + 1


    def list_repositories(
            self,
            product_version_id: int,
            sort: Optional[str] = None,
            page_size: Optional[int] = 100) -> List[Repository]:
        """
        Collect repositories into a list, automatically iterating all pages when pagination is unset.

        :param product_version_id: Product version identifier.
        :param sort: Optional sort order (`asc`, `desc`).
        :param page_size: Items per page for pagination. Defaults to 100.
        :returns: List of repositories.
        """

        return list(
            self.iter_repositories(
                product_version_id=product_version_id,
                sort=sort,
                page_size=page_size,
            ),
        )


    def create_repository(
            self,
            product_version_id: int,
            payload: RepositoryCreate) -> Repository:
        """
        Create a repository for a product version.

        :param product_version_id: Product version identifier.
        :param payload: Repository payload.
        :returns: Newly created repository.
        """

        return self._POST(
            f'/product_versions/{product_version_id}/files',
            payload=payload,
            model=Repository,
            unwrap_data=True,
        )


    def get_repository(self, file_id: int) -> Repository:
        """
        Retrieve a repository (file) by identifier.

        :param file_id: File identifier.
        :returns: Repository representation.
        """

        return self._GET(
            f'/files/{file_id}',
            model=Repository,
            unwrap_data=True,
        )


    def update_repository(
            self,
            file_id: int,
            payload: RepositoryCreate) -> Repository:
        """
        Update a repository (file).

        :param file_id: File identifier.
        :param payload: Updated repository payload.
        :returns: Updated repository.
        """

        return self._PUT(
            f'/files/{file_id}',
            payload=payload,
            model=Repository,
            unwrap_data=True,
        )


    def delete_repository(self, file_id: int) -> None:
        """
        Delete a repository (file).

        :param file_id: File identifier.
        """

        self._DELETE(f'/files/{file_id}')


    def search_files(
            self,
            product_id: Optional[int] = None,
            version_id: Optional[int] = None,
            description: Optional[str] = None,
            file_name: Optional[str] = None,
            jira: Optional[str] = None,
            content_type: Optional[str] = None,
            jboss_id: Optional[int] = None,
            page: Optional[int] = None,
            limit: Optional[int] = None) -> PaginatedRepositoryResults:
        """
        Search files by various metadata.

        :param product_id: Product ID (exact match).
        :param version_id: Product version ID (exact match).
        :param description: Description (glob pattern, case-insensitive).
        :param file_name: File name (glob pattern, case-insensitive).
        :param jira: Jira issue ID (e.g. TUSC-1234).
        :param content_type: Content type (array inclusion check).
        :param jboss_id: JBoss ID (exact match).
        :param page: Page number used for pagination.
        :param limit: Items per page for pagination.
        :returns: Paginated repository (file) search results.
        """

        params = self._build_search_params(
            page=page,
            limit=limit,
            product_id=product_id,
            version_id=version_id,
            description=description,
            file_name=file_name,
            jira=jira,
            content_type=content_type,
            jboss_id=jboss_id,
        )

        return self._GET(
            '/files/search',
            params=params,
            model=PaginatedRepositoryResults,
        )


    @staticmethod
    def _build_list_params(
            page: Optional[int],
            limit: Optional[int],
            sort: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Build pagination parameters for list endpoints.

        ``sort`` defaults to ``asc`` (ID ascending) when omitted; the query
        always includes an explicit ``sort`` value.
        """

        params: Dict[str, Any] = {}

        if page is not None:
            params['page'] = page

        if limit is not None:
            params['limit'] = limit

        params['sort'] = 'asc' if sort is None else sort

        return params or None


    @staticmethod
    def _build_search_params(
            page: Optional[int],
            limit: Optional[int],
            **search_params: Any) -> Dict[str, Any]:
        """
        Build query params for search endpoints; excludes None values.
        """

        params: Dict[str, Any] = {
            k: v for k, v in search_params.items() if v is not None
        }
        if page is not None:
            params['page'] = page
        if limit is not None:
            params['limit'] = limit
        return params


    def _request(
            self,
            method: str,
            path: str,
            payload: Optional[Any] = None,
            model: Optional[Any] = None,
            params: Optional[Dict[str, Any]] = None,
            unwrap_data: bool = False) -> Any:
        """
        Generic REST request wrapper.

        When ``unwrap_data`` is True and the JSON body is a dict with a
        ``data`` key, the value of ``data`` is used for model validation
        instead of the full body. This compensates for APIs that wrap the
        payload in a ``data`` attribute when the spec does not.
        """

        if not path.startswith('/'):
            raise ValueError(f"Expected absolute path starting with '/': {path}")

        url = f"{self._base_url}{path}"

        if isinstance(payload, BaseModel):
            payload = payload.model_dump(
                by_alias=False,
                exclude_none=True,
            )

        response = self._session.request(
            method=method,
            url=url,
            params=params,
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')

        if content_type.startswith('application/json'):
            data = response.json()

            logger.debug(f'[DEBUG] {data}:')

            if unwrap_data and isinstance(data, dict) and 'data' in data:
                data = data['data']
            if model:
                return coerce_model(data, model)
            return data

        return response.content if response.content else None


def coerce_model(data: Any, model: Any) -> Any:
    """
    Convert JSON data into the requested model shape.
    """

    if callable(model):
        return model(**data)

    origin = get_origin(model)
    if origin in (list, List):
        args = get_args(model)
        if not args:
            return data
        element_model: Type[BaseModel] = args[0]
        return [element_model.model_validate(item) for item in data]

    if isinstance(model, type) and issubclass(model, BaseModel):
        return model.model_validate(data)

    assert False, f"Unsupported model type: {model}"


# The end.
