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
from typing import Any, Dict, Iterator, List, Optional, Type, Union

try:
    from typing import get_args, get_origin
except ImportError:
    def get_origin(annotation: Any) -> Optional[Any]:
        return getattr(annotation, '__origin__', None)


    def get_args(annotation: Any) -> tuple:
        return getattr(annotation, '__args__', ())

import requests
from pydantic import BaseModel

from .config import UDConfig
from .models import (
    PaginatedProducts,
    PaginatedRepositories,
    Product,
    ProductCreate,
    Repository,
    RepositoryCreate,
    Version,
    VersionCreate,
    ResponseVersions,
)


logger = logging.getLogger('UDClient')

Payload = Union[
    Product,
    ProductCreate,
    Version,
    VersionCreate,
    Repository,
    RepositoryCreate,
    Dict[str, Any],
]


class UDClient:
    """
    REST client bound to a user configuration.
    """

    def __init__(self, config: UDConfig, session: Optional[requests.Session] = None) -> None:
        """
        Initialize the client with the given configuration.

        :param config: Resolved configuration detailing server and client certificate information.
        :param session: Optional pre-configured requests session for dependency injection.
        """

        self._config = config

        self._session = session or requests.Session()
        self._session.cert = (
            str(config.client_cert),
            str(config.client_key),
        )
        self._session.headers.setdefault('Accept', 'application/json')
        self._session.headers.setdefault('Content-Type', 'application/json')

        if config.ca_cert is not None:
            verify = str(config.ca_cert)
        else:
            verify = config.verify
        self._session.verify = verify

        logger.debug(f"verify: {verify}")
        logger.debug(f"config.ca_cert: {config.ca_cert}")
        logger.debug(f"config.verify: {config.verify}")
        logger.debug(f"config.client_cert: {config.client_cert}")
        logger.debug(f"config.client_key: {config.client_key}")
        logger.debug(f"config.base_url: {config.base_url}")
        logger.debug(f"config.timeout: {config.timeout}")
        logger.debug(f"config.name: {config.name}")

        self._timeout = config.timeout

        self._base_url = config.base_url.rstrip('/')


    def GET(self, path: str, **kwargs: Any) -> Any:
        """
        Make a GET request to the given path.
        """

        return self._request('GET', path, **kwargs)


    def POST(self, path: str, **kwargs: Any) -> Any:
        """
        Make a POST request to the given path.
        """

        return self._request('POST', path, **kwargs)


    def PUT(self, path: str, **kwargs: Any) -> Any:
        """
        Make a PUT request to the given path.
        """

        return self._request('PUT', path, **kwargs)


    def DELETE(self, path: str, **kwargs: Any) -> Any:
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

        return self.GET('/products', params=params, model=PaginatedProducts)


    def iter_products(
            self,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None) -> Iterator[Product]:
        """
        Iterate over products, lazily requesting additional pages.

        :param page: Optional explicit page number. When provided, only that page is requested.
        :param limit: Items per page for pagination.
        :param sort: Optional sort order (`asc`, `desc`).
        """

        explicit_page = page is not None
        next_page = page if explicit_page else 1
        current_limit = limit

        while True:
            page_obj = self.page_products(
                page=next_page,
                limit=current_limit,
                sort=sort,
            )

            for product in page_obj.data:
                yield product

            if explicit_page:
                break

            if page_obj.total_pages <= 1 or page_obj.page >= page_obj.total_pages:
                break

            next_page = page_obj.page + 1
            current_limit = page_obj.limit


    def list_products(
            self,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None) -> List[Product]:
        """
        Collect products into a list, automatically iterating all pages when pagination is unset.

        :param page: Optional explicit page number. When provided, only that page is requested.
        :param limit: Items per page for pagination.
        :param sort: Optional sort order (`asc`, `desc`).
        :returns: List of products.
        """

        return list(self.iter_products(page=page, limit=limit, sort=sort))


    def create_product(self, payload: Payload) -> Product:
        """
        Create a product resource.

        :param payload: Product payload matching API expectations.
        :returns: Newly created product.
        """

        return self.POST('/products', payload=payload, model=Product)


    def get_product(self, product_id: int) -> Product:
        """
        Retrieve a product by identifier.

        :param product_id: Product identifier.
        :returns: Product representation.
        """

        return self.GET(f'/products/{product_id}', model=Product)


    def update_product(self, product_id: int, payload: Payload) -> Product:
        """
        Update an existing product.

        :param product_id: Product identifier.
        :param payload: Updated product payload.
        :returns: Updated product.
        """

        return self.PUT(f'/products/{product_id}', payload=payload, model=Product)


    def delete_product(self, product_id: int) -> None:
        """
        Delete a product.

        :param product_id: Product identifier.
        """

        self.DELETE(f'/products/{product_id}')


    def list_product_versions(self, product_id: int) -> List[Version]:
        """
        Retrieve versions for a product.

        :param product_id: Product identifier.
        :returns: Versions associated with the product.
        """

        response = self.GET(
            f'/products/{product_id}/product_versions',
            model=ResponseVersions,
        )

        return list(response.data)


    def create_product_version(
            self,
            product_id: int,
            payload: Payload) -> Version:
        """
        Create a product version.

        :param product_id: Product identifier.
        :param payload: Version payload.
        :returns: Newly created version.
        """

        return self.POST(
            f'/products/{product_id}/product_versions',
            payload=payload,
            model=Version,
        )


    def get_product_version(self, product_id: int, version_id: int) -> Version:
        """
        Retrieve a product version.

        :param product_id: Product identifier.
        :param version_id: Version identifier.
        :returns: Version representation.
        """

        return self.GET(
            f'/products/{product_id}/product_versions/{version_id}',
            model=Version,
        )


    def update_product_version(
            self,
            product_id: int,
            version_id: int,
            payload: Payload) -> Version:
        """
        Update a product version.

        :param product_id: Product identifier.
        :param version_id: Version identifier.
        :param payload: Updated version payload.
        :returns: Updated version.
        """

        return self.PUT(
            f'/products/{product_id}/product_versions/{version_id}',
            payload=payload,
            model=Version,
        )


    def delete_product_version(self, product_id: int, version_id: int) -> None:
        """
        Delete a product version.

        :param product_id: Product identifier.
        :param version_id: Version identifier.
        """

        self.DELETE(f'/products/{product_id}/product_versions/{version_id}')


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

        return self.GET(
            f'/product_versions/{product_version_id}/repositories',
            params=params,
            model=PaginatedRepositories,
        )


    def iter_repositories(
            self,
            product_version_id: int,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None) -> Iterator[Repository]:
        """
        Iterate over repositories for a product version, lazily requesting additional pages.

        :param product_version_id: Product version identifier.
        :param page: Optional explicit page number. When provided, only that page is requested.
        :param limit: Items per page for pagination.
        :param sort: Optional sort order (`asc`, `desc`).
        """

        explicit_page = page is not None
        next_page = page if explicit_page else 1
        current_limit = limit

        while True:
            page_obj = self.page_repositories(
                product_version_id=product_version_id,
                page=next_page,
                limit=current_limit,
                sort=sort,
            )

            for repository in page_obj.data:
                yield repository

            if explicit_page:
                break

            if page_obj.total_pages <= 1 or page_obj.page >= page_obj.total_pages:
                break

            next_page = page_obj.page + 1
            current_limit = page_obj.limit


    def list_repositories(
            self,
            product_version_id: int,
            page: Optional[int] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None) -> List[Repository]:
        """
        Collect repositories into a list, automatically iterating all pages when pagination is unset.

        :param product_version_id: Product version identifier.
        :param page: Optional explicit page number. When provided, only that page is requested.
        :param limit: Items per page for pagination.
        :param sort: Optional sort order (`asc`, `desc`).
        :returns: List of repositories.
        """

        return list(
            self.iter_repositories(
                product_version_id=product_version_id,
                page=page,
                limit=limit,
                sort=sort,
            ),
        )


    def create_repository(
            self,
            product_version_id: int,
            payload: Payload) -> Repository:
        """
        Create a repository for a product version.

        :param product_version_id: Product version identifier.
        :param payload: Repository payload.
        :returns: Newly created repository.
        """

        return self.POST(
            f'/product_versions/{product_version_id}/repositories',
            payload=payload,
            model=Repository,
        )


    def get_repository(
            self,
            product_version_id: int,
            repository_id: int) -> Repository:
        """
        Retrieve a repository by identifier.

        :param product_version_id: Product version identifier.
        :param repository_id: Repository identifier.
        :returns: Repository representation.
        """

        return self.GET(
            f'/product_versions/{product_version_id}/repositories/{repository_id}',
            model=Repository,
        )


    def update_repository(
            self,
            product_version_id: int,
            repository_id: int,
            payload: Payload) -> Repository:
        """
        Update a repository.

        :param product_version_id: Product version identifier.
        :param repository_id: Repository identifier.
        :param payload: Updated repository payload.
        :returns: Updated repository.
        """

        return self.PUT(
            f'/product_versions/{product_version_id}/repositories/{repository_id}',
            payload=payload,
            model=Repository,
        )


    def delete_repository(
            self,
            product_version_id: int,
            repository_id: int) -> None:
        """
        Delete a repository.

        :param product_version_id: Product version identifier.
        :param repository_id: Repository identifier.
        """

        self.DELETE(
            f'/product_versions/{product_version_id}/repositories/{repository_id}',
        )


    @staticmethod
    def _build_list_params(
            page: Optional[int],
            limit: Optional[int],
            sort: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Build pagination parameters for list endpoints.
        """

        params: Dict[str, Any] = {}

        if page is not None:
            params['page'] = page

        if limit is not None:
            params['limit'] = limit

        if sort is not None:
            params['sort'] = sort

        return params or None


    def _request(
            self,
            method: str,
            path: str,
            payload: Optional[Payload] = None,
            model: Optional[Any] = None,
            params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Generic REST request wrapper.
        """

        if not path.startswith('/'):
            raise ValueError(f"Expected absolute path starting with '/': {path}")

        url = f"{self._base_url}{path}"

        if isinstance(payload, BaseModel):
            payload = payload.model_dump(
                by_alias=True,
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
            if model:
                return coerce_model(data, model)
            return data

        return response.content if response.content else None


def coerce_model(data: Any, model: Any) -> Any:
    """
    Convert JSON data into the requested model shape.
    """

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
