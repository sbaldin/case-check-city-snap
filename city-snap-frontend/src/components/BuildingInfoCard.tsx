import type { BuildingInfo } from '../types/building';

interface BuildingInfoCardProps {
  building: BuildingInfo | null;
  sources: string[];
  fallbackTitle?: string;
}

const BuildingInfoCard = ({ building, sources, fallbackTitle }: BuildingInfoCardProps) => {
  if (!building) {
    return (
      <section className="card shadow-sm mt-5 p-5 text-center">
        <div className="mb-3">
          <span className="fs-1" role="img" aria-label="Историческое здание">
            🏛️
          </span>
        </div>
        <h4>Информация о здании</h4>
        <p className="text-muted">
          Загрузите фотографию и укажите адрес, чтобы получить подробную историческую информацию о здании.
        </p>
      </section>
    );
  }

  const { name, history, architect, year_built: yearBuilt, location, image_path: imagePath } = building;
  const displayName = name ?? fallbackTitle ?? 'Неизвестный объект';

  return (
    <section className="mt-5">
      <div className="row g-4">
        <div className="col-md-6">
          <div className="card shadow-sm h-100">
            {imagePath ? (
              <img src={imagePath} className="card-img-top" alt={name ?? 'Фото здания'} />
            ) : (
              <div className="card-img-top d-flex align-items-center justify-content-center bg-light" style={{ height: '240px' }}>
                <span className="text-muted">Изображение будет доступно после загрузки фотографии</span>
              </div>
            )}
            <div className="card-body">
              <h5 className="card-title">{displayName}</h5>
              {history ? <p className="card-text">{history}</p> : <p className="text-muted mb-0">Историческое описание отсутствует</p>}
            </div>
          </div>
        </div>
        <div className="col-md-6 d-flex flex-column gap-3">
          <div className="card shadow-sm p-3">
            <h6 className="text-success">Год постройки</h6>
            <p className="mb-0 fs-5">{yearBuilt ?? '—'}</p>
            <small className="text-muted">По данным источников</small>
          </div>
          <div className="card shadow-sm p-3">
            <h6 className="text-primary">Архитектор</h6>
            <p className="mb-0">{architect ?? '—'}</p>
            <small className="text-muted">Уточните данные в архиве, если требуется</small>
          </div>
          <div className="card shadow-sm p-3">
            <h6>Координаты</h6>
            {location ? (
              <p className="mb-0">
                {location.lat.toFixed(6)}, {location.lon.toFixed(6)}
              </p>
            ) : (
              <p className="mb-0 text-muted">Координаты не найдены</p>
            )}
          </div>
          <div className="card shadow-sm p-3">
            <h6>Источники данных</h6>
            {sources.length ? (
              <ul className="mb-0">
                {sources.map((source) => (
                  <li key={source}>{source}</li>
                ))}
              </ul>
            ) : (
              <p className="mb-0 text-muted">Источники не указаны</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default BuildingInfoCard;
