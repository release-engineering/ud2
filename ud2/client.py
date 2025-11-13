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
from .models import Product, Repository, Version


logger = logging.getLogger('UDClient')

Payload = Union[Product, Version, Repository, Dict[str, Any]]


class UDClient:
    """
    REST client bound to a user configuration.
    """

    def __init__(self, config: UDConfig, session: Optional[requests.Session] = None) -> None:
        """
        Initialize the client with the given configuration.

        :param config: Resolved configuration detailing server and certificate information.
        :param session: Optional pre-configured requests session for dependency injection.
        """

        self._config = config

        self._session = session or requests.Session()
        self._session.cert = str(config.certificate)
        self._session.headers.setdefault('Accept', 'application/json')
        self._session.headers.setdefault('Content-Type', 'application/json')

        self._timeout = config.timeout
        self._session.verify = config.verify

        self._base_url = config.base_url.rstrip('/')


    def GET(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Make a GET request to the given path.
        """

        return self._request('GET', path, **kwargs)


    def POST(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Make a POST request to the given path.
        """

        return self._request('POST', path, **kwargs)


    def PUT(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Make a PUT request to the given path.
        """

        return self._request('PUT', path, **kwargs)


    def DELETE(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Make a DELETE request to the given path.
        """

        return self._request('DELETE', path, **kwargs)


    def create_product(self, payload: Product) -> Any:
        """
        Create a product resource.
        """

        return self.POST('product', payload=payload)


    def update_product(
            self,
            identifier: str,
            payload: Product) -> Any:
        """
        Update an existing product resource.
        """

        return self.PUT('product', identifier=identifier, payload=payload)


    def delete_product(self, identifier: str) -> Any:
        """
        Delete a product resource.
        """

        return self.DELETE('product', identifier=identifier)


    def list_products(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        List product resources.
        """

        return self.GET('product', params=params)


    def search_products(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Search for product resources.
        """

        return self.GET('product/search', params=params)


    def create_version(self, payload: Version) -> Any:
        """
        Create a version resource.
        """

        return self.POST('version', payload=payload)


    def update_version(
            self,
            identifier: str,
            payload: Version) -> Any:
        """
        Update an existing version resource.
        """

        return self.PUT('version', identifier=identifier, payload=payload)


    def delete_version(self, identifier: str) -> Any:
        """
        Delete a version resource.
        """

        return self.DELETE('version', identifier=identifier)


    def list_versions(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        List version resources.
        """

        return self.GET('version', params=params)


    def search_versions(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Search for version resources.
        """

        return self.GET('version/search', params=params)


    def create_repository(self, payload: Repository) -> Any:
        """
        Create a repository resource.
        """

        return self.POST('repository', payload=payload)


    def update_repository(
            self,
            identifier: str,
            payload: Repository) -> Any:
        """
        Update an existing repository resource.
        """
        return self.PUT('repository', identifier=identifier, payload=payload)


    def delete_repository(self, identifier: str) -> Any:
        """
        Delete a repository resource.
        """

        return self.DELETE('repository', identifier=identifier)


    def list_repositories(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        List repository resources.
        """

        return self.GET('repository', params=params)


    def search_repositories(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Search for repository resources.
        """

        return self.GET('repository/search', params=params)


    def _request(
            self,
            method: str,
            resource: str,
            identifier: Optional[str] = None,
            payload: Optional[Payload] = None,
            model: Optional[Any] = None,
            params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Generic REST request wrapper.
        """

        url = f"{self._base_url}/{resource}"
        if identifier:
            url += f"/{identifier}"

        if isinstance(payload, BaseModel):
            payload = payload.model_dump(exclude_none=True)

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
