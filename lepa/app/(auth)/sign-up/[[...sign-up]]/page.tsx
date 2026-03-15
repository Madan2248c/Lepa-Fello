import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <SignUp
      forceRedirectUrl="/dashboard"
      appearance={{
        variables: {
          colorPrimary: "#FF5A5F",
          colorBackground: "#F7F7F7",
          colorInputBackground: "#FFFFFF",
          colorInputText: "#484848",
          colorText: "#484848",
          colorTextSecondary: "#767676",
          borderRadius: "6px",
        },
        elements: {
          rootBox: "mx-auto",
          card: "bg-white border border-[#DDDDDD] shadow-sm",
        },
      }}
    />
  );
}
