interface ErrorMessageProps {
  title?: string;
  message: string;
}

const ErrorMessage = ({ title = 'Что-то пошло не так', message }: ErrorMessageProps) => (
  <div className="alert alert-danger" role="alert">
    <strong>{title}.</strong> {message}
  </div>
);

export default ErrorMessage;
