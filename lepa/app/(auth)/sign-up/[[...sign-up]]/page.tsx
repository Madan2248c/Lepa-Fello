import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <SignUp
      appearance={{
        variables: {
          colorPrimary: "#5B9BD5",
          colorBackground: "#1C1D20",
          colorInputBackground: "#161719",
          colorInputText: "#E8E9EA",
          colorText: "#E8E9EA",
          colorTextSecondary: "#9B9A97",
          borderRadius: "8px",
        },
        elements: {
          rootBox: "mx-auto",
          card: "bg-[#1C1D20] border border-[rgba(255,255,255,0.06)] shadow-xl",
        },
      }}
    />
  );
}
