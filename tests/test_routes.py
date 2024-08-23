"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from service import app, talisman
from service.models import db, Account, init_db, DataValidationError
from service.common import status  # HTTP Status Codes
from tests.factories import AccountFactory
from flask import abort

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        talisman.force_https = False

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_read_an_account(self):
        """It should Read a single Account"""
        account = self._create_accounts(1)[0]  # Create a test account
        resp = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], account.name)

    def test_get_account(self):
        """It should Read a single Account"""
        account = self._create_accounts(1)[0]
        resp = self.client.get(
            f"{BASE_URL}/{account.id}", content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], account.name)

    def test_get_account_not_found(self):
        """It should not Read an Account that is not found"""
        resp = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_account_with_invalid_id(self):
        """It should return 404 for invalid account ID"""
        resp = self.client.get(f"{BASE_URL}/invalid")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_account_fields(self):
        """It should return all fields of an account"""
        account = self._create_accounts(1)[0]
        resp = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["id"], account.id)
        self.assertEqual(data["name"], account.name)
        self.assertEqual(data["email"], account.email)
        self.assertEqual(data["address"], account.address)
        self.assertEqual(data["phone_number"], account.phone_number)
        self.assertEqual(data["date_joined"], str(account.date_joined))

    def test_method_not_allowed(self):
        """It should handle Method Not Allowed error"""
        resp = self.client.put(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        data = resp.get_json()
        self.assertEqual(data["error"], "Method not Allowed")

    def test_internal_server_error(self):
        """It should handle Internal Server Error"""
        @app.route("/error")
        def error():
            abort(500, "Internal Server Error")

        resp = self.client.get("/error")
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = resp.get_json()
        self.assertEqual(data["status"], 500)
        self.assertEqual(data["error"], "Internal Server Error")

    def test_deserialize_with_key_error(self):
        """It should not Deserialize an account with a KeyError"""
        account = Account()
        self.assertRaises(DataValidationError, account.deserialize, {})

    def test_deserialize_with_type_error(self):
        """It should not Deserialize an account with a TypeError"""
        account = Account()
        self.assertRaises(DataValidationError, account.deserialize, [])

    def test_get_account_list(self):
        """It should Get a list of Accounts"""
        self._create_accounts(5)
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 5)

    def test_logging_handler(self):
        """It should have a logging handler"""
        app.logger.addHandler(logging.NullHandler())
        self.assertTrue(len(app.logger.handlers) >= 1)

    def test_deserialize_with_no_name(self):
        """It should not deserialize an Account with no name"""
        data = {"email": "test@example.com"}
        account = Account()
        self.assertRaises(DataValidationError, account.deserialize, data)

    def test_deserialize_with_no_data(self):
        """It should not deserialize empty data"""
        account = Account()
        self.assertRaises(DataValidationError, account.deserialize, None)

    def test_deserialize_with_bad_data(self):
        """It should not deserialize bad data"""
        account = Account()
        self.assertRaises(DataValidationError, account.deserialize, "data")

    def test_app_configuration(self):
        """It should be properly configured"""
        self.assertTrue(app.config['TESTING'])
        self.assertFalse(app.config['DEBUG'])
        self.assertIsNotNone(app.config['SQLALCHEMY_DATABASE_URI'])

    def test_media_type_not_supported(self):
        """It should handle unsupported media type"""
        resp = self.client.post(BASE_URL, json={}, content_type='application/xml')
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        data = resp.get_json()
        self.assertEqual(data["error"], "Unsupported media type")

    def test_account_create_with_no_name(self):
        """It should not create an Account without a name"""
        account = Account(email="test@example.com")
        self.assertRaises(DataValidationError, account.create)

    def test_account_update_with_no_name(self):
        """It should not update an Account without a name"""
        account = self._create_accounts(1)[0]
        account.name = ""
        self.assertRaises(DataValidationError, account.update)

    def test_account_delete(self):
        """It should delete an Account"""
        account = AccountFactory()
        account.create()
        account_id = account.id
        account.delete()
        self.assertIsNone(Account.find(account_id))

    def test_app_initialization(self):
        """It should initialize the app"""
        self.assertIsNotNone(app)
        self.assertIsNotNone(app.config)
        self.assertTrue(app.config['TESTING'])
        self.assertFalse(app.config['DEBUG'])

    def test_unsupported_media_type(self):
        """It should handle unsupported media type"""
        resp = self.client.post(BASE_URL, data="bad data", content_type="text/html")
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        data = resp.get_json()
        self.assertEqual(data["error"], "Unsupported media type")

    def test_deserialize_with_invalid_attributes(self):
        """It should not deserialize an Account with invalid attributes"""
        data = {"name": "John", "foo": "bar"}
        account = Account()
        self.assertRaises(DataValidationError, account.deserialize, data)

    def test_get_account_list(self):
        """It should Get a list of Accounts"""
        self._create_accounts(5)
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 5)

    def test_update_account(self):
        """It should Update an existing Account"""
        test_account = AccountFactory()
        resp = self.client.post(BASE_URL, json=test_account.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_account = resp.get_json()
        new_account["name"] = "Updated Name"
        resp = self.client.put(f"{BASE_URL}/{new_account['id']}", json=new_account)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        updated_account = resp.get_json()
        self.assertEqual(updated_account["name"], "Updated Name")

    def test_delete_account(self):
        """It should Delete an Account"""
        account = self._create_accounts(1)[0]
        resp = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(Account.find(account.id))

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)

    def test_cors_security(self):
        """It should return a CORS header"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check for the CORS header
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), '*')