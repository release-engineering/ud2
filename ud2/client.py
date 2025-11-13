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
from typing import Any, Dict, List, Optional, Type, Union

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
        print(f"verify: {verify}")
        print(f"config.ca_cert: {config.ca_cert}")
        print(f"config.verify: {config.verify}")
        print(f"config.client_cert: {config.client_cert}")
        print(f"config.client_key: {config.client_key}")
        print(f"config.base_url: {config.base_url}")
        print(f"config.timeout: {config.timeout}")
        print(f"config.name: {config.name}")

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


    def list_products(
            self,
            params: Optional[Dict[str, Any]] = None) -> PaginatedProducts:
        """
        Retrieve a paginated list of products.

        :param params: Optional pagination parameters (`page`, `limit`, `sort`).
        """

        return self.GET('/products', params=params, model=PaginatedProducts)


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

        return self.GET(
            f'/products/{product_id}/product_versions',
            model=List[Version],
        )


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


    def list_repositories(
            self,
            product_version_id: int,
            params: Optional[Dict[str, Any]] = None) -> PaginatedRepositories:
        """
        Retrieve repositories for a product version.

        :param product_version_id: Product version identifier.
        :param params: Optional pagination parameters (`page`, `limit`, `sort`).
        """

        return self.GET(
            f'/product_versions/{product_version_id}/repositories',
            params=params,
            model=PaginatedRepositories,
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
