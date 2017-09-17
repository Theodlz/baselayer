import pytest
import distutils.spawn
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException
from seleniumrequests.request import RequestMixin
from baselayer.app import models
from baselayer.app.config import Config


def load_test_config(config_paths):
    print('Loading test configuration from _test_config.yaml')
    cfg = Config(config_paths)
    print('Setting test database to:', cfg['database'])
    models.init_db(**cfg['database'])
    MyCustomWebDriver.server_url = cfg['server:url']
    return cfg


class MyCustomWebDriver(RequestMixin, webdriver.Chrome):
    server_url = None

    def get(self, uri):
        return webdriver.Chrome.get(self, self.server_url + uri)

    def wait_for_xpath(self, xpath, timeout=5):
        return WebDriverWait(self, timeout).until(
            expected_conditions.presence_of_element_located((By.XPATH, xpath)))

    def wait_for_xpath_missing(self, xpath, timeout=5):
        return WebDriverWait(self, timeout).until_not(
            expected_conditions.presence_of_element_located((By.XPATH, xpath)))


@pytest.fixture(scope='module', autouse=True)
def driver(request):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    chrome_options = Options()

    chromium = distutils.spawn.find_executable('chromium-browser')

    if chromium:
        chrome_options.binary_location = chromium

    chrome_options.add_argument('--browser.download.folderList=2')
    chrome_options.add_argument(
        '--browser.helperApps.neverAsk.saveToDisk=application/octet-stream')
    prefs = {'download.default_directory': '/tmp'}
    chrome_options.add_experimental_option('prefs', prefs)

    driver = MyCustomWebDriver(chrome_options=chrome_options)
    driver.set_window_size(1920, 1080)

    def close():
        driver.close()

    request.addfinalizer(close)

    # Authenticate by clicking login button
    driver.get('/')
    try:
        driver.wait_for_xpath('//div[contains(text(), "testuser@cesium-ml.org")]')
    except TimeoutException:
        # Already logged in
        element = WebDriverWait(driver, 5).until(
            expected_conditions.element_to_be_clickable(
                (By.XPATH, '//a[@href="/login/google-oauth2"]')))
        element.click()

    return driver


@pytest.fixture(scope='function', autouse=True)
def reset_state(request):
    def teardown():
        models.DBSession().rollback()
    request.addfinalizer(teardown)
