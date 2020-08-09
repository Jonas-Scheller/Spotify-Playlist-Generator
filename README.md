# Generate spotify playlists based on your listening habits
This project accesses the spotify api through the spotipy library and enables an easy creation of playlists based on your listening habits. 

Requirements:
- spotipy
- sklearn
- numpy

In order to run the code, you need to create a custom config file with your personal information. There is a template config file "template_config.cfg" in the repository. Follow these simple steps:

1. Register your application to https://developer.spotify.com/documentation/general/guides/app-settings/#register-your-app
2. Rename "template_conig.cfg" to "config.cfg"
3. Fill out the blank information with the information from your app and enter your username. Make sure the redirect URI is the same as registered in the app 
4. Run the code as presented in the jupyter notebook
5. Enjoy your new playlists!
