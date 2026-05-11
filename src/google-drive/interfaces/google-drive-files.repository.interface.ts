/**
 * Parâmetros para envio de um arquivo binário ao Google Drive.
 */
export interface UploadDriveFileParams {
  buffer: Buffer;
  fileName: string;
  mimeType: string;
  parents?: string[];
}

/**
 * Metadados editáveis de um arquivo no Drive (nome e descrição).
 */
export interface UpdateDriveFileMetadataParams {
  name?: string;
  description?: string;
}

/**
 * Resumo de um arquivo retornado pelas operações do Drive.
 */
export interface DriveFileSummary {
  id: string;
  name: string;
  mimeType: string;
  parents?: string[];
}

/**
 * Abstração das operações de arquivos no Google Drive (infraestrutura).
 */
export interface IGoogleDriveFilesRepository {
  upload(params: UploadDriveFileParams): Promise<DriveFileSummary>;

  updateMetadata(
    fileId: string,
    params: UpdateDriveFileMetadataParams,
  ): Promise<DriveFileSummary>;

  moveToFolder(fileId: string, targetFolderId: string): Promise<DriveFileSummary>;

  delete(fileId: string): Promise<void>;
}

export const GOOGLE_DRIVE_FILES_REPOSITORY = Symbol('GOOGLE_DRIVE_FILES_REPOSITORY');
