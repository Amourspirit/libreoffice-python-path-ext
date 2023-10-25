<p align="center">
<img src="https://github.com/Amourspirit/libreoffice-python-path-ext/assets/4193389/a4470448-0a15-4b6b-8e75-c7ec140fb634" alt="Py Path Extension Logo" width="174" height="174">
</p>

# Include Python Path Extension for LibreOffice

Include extra python paths for LibreOffice python scripts.

On LibreOffice Extensions this extension can be found [here](https://extensions.libreoffice.org/en/extensions/show/41996), locally the extension can is found in the [dist](./dist) folder.

After installing extension and restarting LibreOffice, the extension will be available in the `Tools -> Extension Manager...` dialog.

## Windows Example Tutorial

### Virtual Environment

Using [pyenv](https://github.com/pyenv-win/pyenv-win) for Windows set the environment for the local folder to match the Python major and minor version of LibreOffice.

In this example the folder is `D:\Python\python38`

```powershell
pyenv local 3.8.10
```

Make a virtual environment in `D:\Python\python38`

```powershell
python -m venv venv
```

Activate the virtual environment

```powershell
.\venv\Scripts\Activate.ps1
```

Should see a prompt similar to:
```powershell
(venv) [D:\Python\python38\]
```

Pip install python package(s) into the virtual environment.

```powershell
pip install ooo-dev-tools
```

### LibreOffice

#### Add Path

Start LibreOffice and open the extension manager `Tools -> Extension Manager...` Select `LibreOffice Python Path` Extension.
Click on `Options`.

![2023-10-25_0-03-27-2](https://github.com/Amourspirit/libreoffice-python-path-ext/assets/4193389/25afb530-2304-413d-aa44-121e4c249b92)

Select the `Python Paths` option page.

![2023-10-25_0-26-25](https://github.com/Amourspirit/libreoffice-python-path-ext/assets/4193389/a370746f-9e9a-41f8-aefa-3f1a987a3fb7)

Choose `Add Folder` and navigate to the Location of the `site-packages` for the virtual environment that was set up previously.

![2023-10-25_0-28-26](https://github.com/Amourspirit/libreoffice-python-path-ext/assets/4193389/918ceb02-765b-47a0-9908-fedea66caef7)


Now the path is added to the extension. 
![2023-10-25_0-29-10](https://github.com/Amourspirit/libreoffice-python-path-ext/assets/4193389/25abc42e-89d8-4fcc-8dfe-887ad7eb4c4b)

Click `OK` and restart LibreOffice and the path will be added to LibreOffice when it starts.

#### APSO

Using the [APSO](https://extensions.libreoffice.org/en/extensions/show/apso-alternative-script-organizer-for-python) console the import can be tested.

![2023-10-25_0-46-33](https://github.com/Amourspirit/libreoffice-python-path-ext/assets/4193389/a61282c0-7197-4b78-a8b4-b0b4810b1b3f)

## Dev Container

This project is generated from [Python LibreOffice Pip Extension Template](https://github.com/Amourspirit/python-libreoffice-pip) which in turn was generated from the [Live LibreOffice Python Template] This means this project can be run/developed in a Development container or Codespace with full access to LibreOffice.

### Accessing LibreOffice

The ports to access LibreOffice are `3050` for http and `3051` for https.

See also: [How do I access the LibreOffice in a GitHub Codespace?](https://github.com/Amourspirit/live-libreoffice-python/wiki/FAQ#how-do-i-access-the-libreoffice-in-a-github-codespace) on [Live LibreOffice Python Template].

## Installing Extension

From LibreOffice open the extension manager, `Tools -> Extension Manager ...` and add `PyPath.oxt`

When prompted choose `Only for me`. Restart LibreOffice and extension will install.

![Add Extension Dialog](https://github.com/Amourspirit/libreoffice-python-path-ext/assets/4193389/1755df5c-b5f9-461c-bcd8-d0e1e7772da5)

![For whom do you want to install the extension dialog box](https://github.com/Amourspirit/python-libreoffice-numpy-ext/assets/4193389/ee0369a2-f2f9-45d9-b093-66a138078f2a)

[Live LibreOffice Python Template]:https://github.com/Amourspirit/live-libreoffice-python