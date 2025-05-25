from kiteconnect import KiteConnect
import os

api_key = "wzpxu24i12m84kgp"
api_secret = "unh0zs6j2r2uqhf2fdogowrxz1vga014"
token_path = os.path.join(os.path.dirname(__file__), "..", "access_token.txt")

kite = KiteConnect(api_key=api_key)

print("Open this URL in your browser and login:")
print(kite.login_url())

request_token = input("Enter the request_token from redirected URL: ")

try:
    data = kite.generate_session(request_token, api_secret=api_secret)
    access_token = data["access_token"]

    with open(token_path, "w") as f:
        f.write(access_token)
    print(f"Access token saved to {token_path}")

except Exception as e:
    print(f"Error generating session: {e}")
