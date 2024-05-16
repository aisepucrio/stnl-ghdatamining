import customtkinter

customtkinter.set_appearance_mode('dark')
customtkinter.set_default_color_theme("dark-blue")

root = customtkinter.CTk()
root.geometry("500x350")

def login():
    print("Test")

frame = customtkinter.CTkFrame(master=root)
frame.pack(padx=10, pady=10, fill="both", expand=True)

label = customtkinter.CTkLabel(master=frame, text="Username")
label.pack(pady=12, padx=10)

entry_1 = customtkinter.CTkEntry(master=frame, placeholder_text='Username')
entry_1.pack(pady=12, padx=10)

entry_2 = customtkinter.CTkEntry(master=frame, placeholder_text='Password', show='*')
entry_2.pack(pady=12, padx=10)

button = customtkinter.CTkButton(master=frame, text="Login", command=login)
button.pack(pady=12, padx=10)

checkbox = customtkinter.CTkCheckBox(master=frame, text="Remember me")
checkbox.pack(pady=12, padx=10)

root.mainloop()