import Swal from "sweetalert2";

// One themed instance so every popup matches the console-and-paper design.
const themed = Swal.mixin({
  background: "#181c25",
  color: "#dde2ec",
  confirmButtonColor: "#d9a441",
  cancelButtonColor: "#2a3040",
});

export const toastError = (message) =>
  themed.fire({
    toast: true,
    position: "bottom-end",
    icon: "error",
    title: message,
    showConfirmButton: false,
    timer: 4500,
    timerProgressBar: true,
  });

export const confirmDialog = async ({ title, text, confirmText = "Yes" }) => {
  const result = await themed.fire({
    title,
    text,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: confirmText,
  });
  return result.isConfirmed;
};

export default themed;
