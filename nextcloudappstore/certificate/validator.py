"""
SPDX-FileCopyrightText: 2017 Nextcloud GmbH and Nextcloud contributors
SPDX-License-Identifier: AGPL-3.0-or-later
"""

import logging
from base64 import b64decode

import pem
from django.conf import settings  # type: ignore
from OpenSSL.crypto import (
    FILETYPE_PEM,
    X509,
    X509Store,
    X509StoreContext,
    X509StoreFlags,
    load_certificate,
    load_crl,
    verify,
)
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class CertificateConfiguration:
    def __init__(self) -> None:
        self.digest = settings.CERTIFICATE_DIGEST


class InvalidSignatureException(ValidationError):
    pass


class InvalidCertificateException(ValidationError):
    pass


class CertificateAppIdMismatchException(ValidationError):
    pass


class CertificateValidator:
    """
    See https://pyopenssl.readthedocs.io/en/stable/api/crypto.html#signing
    -and-verifying-signatures
    """

    def __init__(self, config: CertificateConfiguration) -> None:
        self.config = config

    def validate_signature(self, certificate: str, signature: str, data: bytes) -> None:
        """
        Tests if a value is a valid certificate using the provided hash
        algorithm
        :param certificate: the certificate to use as string
        :param signature: the signature base64 encoded string to test
        :param data: the binary file content that was signed
        :raises: InvalidSignatureException if the signature is invalid
        :return: None
        """
        cert = self._to_cert(certificate)
        err_msg = "Signature is invalid"
        try:
            verify(cert, b64decode(signature.encode()), data, self.config.digest)
        except Exception as e:
            raise InvalidSignatureException(f"{err_msg}: {str(e)}")

    def validate_certificate(self, certificate: str, chain: str, crl: str | None = None) -> None:
        """
        Tests if a certificate has been signed by the chain, is not revoked
        and has not yet been expired.
        :param certificate: the certificate to test as string
        :param chain: the certificate chain file content as string
        :param crl: the certificate revocation list file content as string
        :raises: InvalidCertificateException if the certificate is invalid
        :return: None
        """
        # root and intermediary certificate need to be split
        cas = pem.parse(chain.encode())
        store = X509Store()
        for ca in cas:
            store.add_cert(self._to_cert(str(ca)))

        cert = self._to_cert(certificate)

        if crl:
            parsed_crl = load_crl(FILETYPE_PEM, crl)
            store.set_flags(X509StoreFlags.CRL_CHECK)
            store.add_crl(parsed_crl)

        ctx = X509StoreContext(store, cert)
        err_msg = "Certificate is invalid"

        try:
            ctx.verify_certificate()
        except Exception as e:
            raise InvalidCertificateException(f"{err_msg}: {str(e)}")

    def get_cn(self, certificate: str) -> str:
        """
        Extracts the CN from a certificate and removes the leading
        slash, e.g. /news should return news
        :param certificate: certificate
        :return: the certificate's subject without the leading slash
        """
        cert = self._to_cert(certificate)
        return cert.get_subject().CN

    def validate_app_id(self, certificate: str, app_id: str) -> None:
        """
        Validates if the CN matches the app id
        :param certificate: app certificate
        :param app_id: the app id
        :raises CertificateAppIdMismatchException: if the app id and cert CN do
        not match
        :return: None
        """
        cn = self.get_cn(certificate)
        master_cns = getattr(settings, 'MASTER_CERTIFICATE_CNS', [])
        if cn == app_id:
            return
        if cn in master_cns:
            return
        msg = f"App id {app_id} does not match cert CN {cn}"
        raise CertificateAppIdMismatchException(msg)

    def _to_cert(self, certificate: str) -> X509:
        try:
            return load_certificate(FILETYPE_PEM, certificate.encode())
        except Exception as e:
            msg = "{}: {}".format("Invalid certificate", str(e))
            raise InvalidCertificateException(msg)
