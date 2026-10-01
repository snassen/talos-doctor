# Tailscale: Talos Web on your phone (optional)

Talos Web listens on this Mac only. Tailscale lets your own devices reach it over your private network,
with nothing opened to the internet.

1. Install Tailscale on the Mac and on your phone (https://tailscale.com/download), signed in to the same
   account.
2. Publish Talos Web on your tailnet, on port 8443:

       tailscale serve --bg --https=8443 http://127.0.0.1:7420

3. Tell Talos which name and which people to let in, in `~/TalosData/web.json`:

       {"tailnet_hosts": ["<this-mac>.<your-tailnet>.ts.net"], "tailnet_users": ["you@example.com"]}

   and restart Talos Web.
4. On the phone, open `https://<this-mac>.<your-tailnet>.ts.net:8443` and sign in as usual.

Every page still needs your password and authenticator code; Tailscale only decides who can knock.
