import {
  BadRequestException,
  Body,
  Controller,
  Delete,
  HttpCode,
  HttpStatus,
  Param,
  Patch,
  Post,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';

type UploadedMultipartFile = {
  buffer: Buffer;
  originalname: string;
  mimetype: string;
};
import { GoogleDriveFilesService } from './google-drive-files.service';

const UPLOAD_FIELD = 'file';
const MAX_FILE_SIZE = 50 * 1024 * 1024;

/**
 * Endpoints REST para upload, edição de metadados, movimentação e exclusão de arquivos no Google Drive.
 */
@Controller('google-drive/files')
export class GoogleDriveFilesController {
  constructor(private readonly googleDriveFilesService: GoogleDriveFilesService) {}

  /**
   * Faz upload de um arquivo (multipart, campo `file`). Opcional: `parents` como JSON array de IDs de pasta.
   */
  @Post()
  @UseInterceptors(
    FileInterceptor(UPLOAD_FIELD, {
      limits: { fileSize: MAX_FILE_SIZE },
    }),
  )
  async upload(
    @UploadedFile() file: UploadedMultipartFile | undefined,
    @Body('parents') parentsRaw?: string,
  ) {
    if (!file?.buffer?.length) {
      throw new BadRequestException(`Envie um arquivo no campo multipart "${UPLOAD_FIELD}"`);
    }

    let parents: string[] | undefined;
    if (parentsRaw?.trim()) {
      try {
        const parsed = JSON.parse(parentsRaw) as unknown;
        if (!Array.isArray(parsed) || !parsed.every((p) => typeof p === 'string')) {
          throw new BadRequestException('parents deve ser um JSON array de strings (IDs de pastas)');
        }
        parents = parsed;
      } catch {
        throw new BadRequestException('parents deve ser JSON válido, ex: ["pastaId1"]');
      }
    }

    return this.googleDriveFilesService.uploadFile({
      buffer: file.buffer,
      originalName: file.originalname,
      mimeType: file.mimetype,
      parents,
    });
  }

  /**
   * Atualiza nome e/ou descrição do arquivo no Drive.
   */
  @Patch(':fileId')
  async updateMetadata(
    @Param('fileId') fileId: string,
    @Body() body: { name?: string; description?: string },
  ) {
    return this.googleDriveFilesService.updateMetadata(fileId, {
      name: body?.name,
      description: body?.description,
    });
  }

  /**
   * Move o arquivo para outra pasta (um único parent de destino).
   */
  @Post(':fileId/move')
  async move(
    @Param('fileId') fileId: string,
    @Body() body: { targetFolderId: string },
  ) {
    return this.googleDriveFilesService.moveToFolder(fileId, body?.targetFolderId ?? '');
  }

  /**
   * Remove permanentemente o arquivo do Drive.
   */
  @Delete(':fileId')
  @HttpCode(HttpStatus.NO_CONTENT)
  async remove(@Param('fileId') fileId: string): Promise<void> {
    await this.googleDriveFilesService.deleteFile(fileId);
  }
}
