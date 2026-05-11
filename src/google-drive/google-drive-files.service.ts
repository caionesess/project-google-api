import { BadRequestException, Inject, Injectable, Logger, NotFoundException, ForbiddenException } from '@nestjs/common';
import {
  GOOGLE_DRIVE_FILES_REPOSITORY,
  type DriveFileSummary,
  type IGoogleDriveFilesRepository,
  type UpdateDriveFileMetadataParams,
} from './interfaces/google-drive-files.repository.interface';

const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;

/**
 * Caso de uso de arquivos no Google Drive: validação, erros de domínio e logs.
 */
@Injectable()
export class GoogleDriveFilesService {
  private readonly logger = new Logger(GoogleDriveFilesService.name);

  constructor(
    @Inject(GOOGLE_DRIVE_FILES_REPOSITORY)
    private readonly driveFiles: IGoogleDriveFilesRepository,
  ) {}

  async uploadFile(input: {
    buffer: Buffer;
    originalName: string;
    mimeType: string;
    parents?: string[];
  }): Promise<DriveFileSummary> {
    const { buffer, originalName, mimeType, parents } = input;

    if (!buffer?.length) {
      throw new BadRequestException('Arquivo vazio ou ausente');
    }

    if (buffer.length > MAX_UPLOAD_BYTES) {
      throw new BadRequestException(
        `Arquivo excede o limite de ${MAX_UPLOAD_BYTES} bytes`,
      );
    }

    const fileName = this.sanitizeFileName(originalName);

    try {
      const summary = await this.driveFiles.upload({
        buffer,
        fileName,
        mimeType: mimeType || 'application/octet-stream',
        parents: this.normalizeParents(parents),
      });

      this.logger.log(
        JSON.stringify({ msg: 'drive.upload.ok', fileId: summary.id, fileName: summary.name }),
      );

      return summary;
    } catch (error: unknown) {
      throw this.mapDriveError(error, 'Falha ao enviar arquivo para o Google Drive');
    }
  }

  async updateMetadata(
    fileId: string,
    params: UpdateDriveFileMetadataParams,
  ): Promise<DriveFileSummary> {
    this.assertFileId(fileId);

    if (params.name === undefined && params.description === undefined) {
      throw new BadRequestException('Informe ao menos name ou description para editar');
    }

    if (params.name !== undefined && !params.name.trim()) {
      throw new BadRequestException('name não pode ser vazio');
    }

    try {
      const summary = await this.driveFiles.updateMetadata(fileId, {
        ...(params.name !== undefined ? { name: params.name.trim() } : {}),
        ...(params.description !== undefined ? { description: params.description } : {}),
      });

      this.logger.log(
        JSON.stringify({ msg: 'drive.updateMetadata.ok', fileId: summary.id }),
      );

      return summary;
    } catch (error: unknown) {
      throw this.mapDriveError(error, 'Falha ao editar metadados no Google Drive');
    }
  }

  async moveToFolder(fileId: string, targetFolderId: string): Promise<DriveFileSummary> {
    this.assertFileId(fileId);
    if (!targetFolderId?.trim()) {
      throw new BadRequestException('targetFolderId é obrigatório');
    }

    try {
      const summary = await this.driveFiles.moveToFolder(fileId, targetFolderId.trim());

      this.logger.log(
        JSON.stringify({
          msg: 'drive.move.ok',
          fileId: summary.id,
          parents: summary.parents,
        }),
      );

      return summary;
    } catch (error: unknown) {
      throw this.mapDriveError(error, 'Falha ao mover arquivo no Google Drive');
    }
  }

  async deleteFile(fileId: string): Promise<void> {
    this.assertFileId(fileId);

    try {
      await this.driveFiles.delete(fileId);
      this.logger.log(JSON.stringify({ msg: 'drive.delete.ok', fileId }));
    } catch (error: unknown) {
      throw this.mapDriveError(error, 'Falha ao remover arquivo no Google Drive');
    }
  }

  private assertFileId(fileId: string): void {
    if (!fileId?.trim()) {
      throw new BadRequestException('ID do arquivo é obrigatório');
    }
  }

  private normalizeParents(parents?: string[]): string[] | undefined {
    if (!parents?.length) {
      return undefined;
    }
    const cleaned = parents.map((p) => p.trim()).filter(Boolean);
    return cleaned.length ? cleaned : undefined;
  }

  private sanitizeFileName(name: string): string {
    const base = name?.trim() || 'arquivo';
    return base.replace(/[/\\]/g, '-').slice(0, 255);
  }

  private mapDriveError(error: unknown, fallbackMessage: string): Error {
    const err = error as { code?: number; message?: string; errors?: Array<{ reason?: string }> };

    this.logger.error(
      JSON.stringify({
        msg: 'drive.error',
        code: err.code,
        message: err.message,
      }),
    );

    if (err.code === 404) {
      return new NotFoundException('Arquivo não encontrado no Google Drive');
    }

    if (err.code === 403) {
      return new ForbiddenException(
        'Permissão negada no Google Drive. Verifique se a Service Account tem acesso ao arquivo ou pasta.',
      );
    }

    if (err.message?.includes('invalid_grant') || err.message?.includes('invalid')) {
      return new BadRequestException('Credenciais ou parâmetros inválidos para o Google Drive');
    }

    return new BadRequestException(err.message || fallbackMessage);
  }
}
